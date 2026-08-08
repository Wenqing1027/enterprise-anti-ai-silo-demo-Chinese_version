"""Extraction 控制环：schema → extract → validate。"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agents.extraction.prompts import (
    build_retry_message,
    build_system_prompt,
    build_user_message,
)
from agents.extraction.skill_loader import load_extraction_skill
from agents.extraction.validate import (
    apply_known_ids,
    format_validation_error,
    parse_json_object,
    validate_payload,
)
from shared.llm.client import DeepSeekClient, get_llm_client
from shared.tools.base import ToolContext
from shared.tools.registry import ToolRegistry, default_registry

ROOT = Path(__file__).resolve().parents[2]
TAG_VOCAB_PATH = ROOT / "data" / "vocab" / "tag_vocabulary.json"


@dataclass
class ExtractionResult:
    ok: bool
    skill_id: str
    run_id: str
    stop_reason: str
    payload_schema: str
    payload: dict[str, Any] | None = None
    raw_model_output: str = ""
    final_answer: str = ""
    attempts: int = 0
    warnings: list[str] = field(default_factory=list)
    ai_output_id: str | None = None
    steps: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "skill_id": self.skill_id,
            "run_id": self.run_id,
            "stop_reason": self.stop_reason,
            "payload_schema": self.payload_schema,
            "payload": self.payload,
            "raw_model_output": self.raw_model_output,
            "final_answer": self.final_answer,
            "attempts": self.attempts,
            "warnings": self.warnings,
            "ai_output_id": self.ai_output_id,
            "steps": self.steps,
        }


def _load_tag_assets() -> tuple[set[str], dict[str, dict[str, str]]]:
    if not TAG_VOCAB_PATH.is_file():
        return set(), {}
    raw = json.loads(TAG_VOCAB_PATH.read_text(encoding="utf-8"))
    tags = raw.get("tags") if isinstance(raw, dict) else raw
    allowed: set[str] = set()
    meta: dict[str, dict[str, str]] = {}
    for row in tags or []:
        tid = str(row.get("tag_id") or "")
        if not tid or tid.startswith("TAG-ROOT-"):
            continue
        allowed.add(tid)
        meta[tid] = {
            "tag_name": str(row.get("tag_name") or tid),
            "tag_domain": str(row.get("tag_domain") or ""),
        }
    return allowed, meta


def _normalize_input(user_input: str | dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if isinstance(user_input, dict):
        # seed 文件可能包一层 input
        body = user_input.get("input") if isinstance(user_input.get("input"), dict) else user_input
        assert isinstance(body, dict)
        text = str(body.get("text") or body.get("query") or "").strip()
        known = {
            k: body.get(k)
            for k in ("customer_id", "vin", "channel")
            if body.get(k) not in (None, "")
        }
        return text, known
    return str(user_input or "").strip(), {}


def _message_content(resp: Any) -> str:
    try:
        choice = resp.choices[0]
        content = choice.message.content
        return content if isinstance(content, str) else (content or "")
    except Exception:  # noqa: BLE001
        return ""


class ExtractionAgent:
    def __init__(
        self,
        registry: ToolRegistry | None = None,
        llm: DeepSeekClient | None = None,
    ) -> None:
        self.registry = registry or default_registry
        self.llm = llm

    def run(
        self,
        skill_id: str,
        user_input: str | dict[str, Any],
        *,
        run_id: str | None = None,
        write_output: bool | None = None,
    ) -> ExtractionResult:
        skill = load_extraction_skill(skill_id)
        rid = run_id or f"ext-{uuid.uuid4().hex[:10]}"
        text, known = _normalize_input(user_input)
        steps: list[dict[str, Any]] = []

        if not text:
            return ExtractionResult(
                ok=False,
                skill_id=skill_id,
                run_id=rid,
                stop_reason="bad_input",
                payload_schema=skill.payload_schema,
                final_answer="输入文本为空",
                steps=steps,
            )
        if len(text) > skill.max_input_chars:
            return ExtractionResult(
                ok=False,
                skill_id=skill_id,
                run_id=rid,
                stop_reason="bad_input",
                payload_schema=skill.payload_schema,
                final_answer=f"输入超过 {skill.max_input_chars} 字符，请先切片",
                steps=steps,
            )

        allowed_tags, tag_meta = _load_tag_assets()
        if not allowed_tags:
            return ExtractionResult(
                ok=False,
                skill_id=skill_id,
                run_id=rid,
                stop_reason="config_error",
                payload_schema=skill.payload_schema,
                final_answer="标签字典为空，无法校验 tag_id",
                steps=steps,
            )

        system = build_system_prompt(skill)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": build_user_message(
                    skill_id, skill.payload_schema, text, known=known
                ),
            },
        ]

        client = self.llm or get_llm_client(profile="extraction")
        max_attempts = 1 + int(skill.max_schema_retries)
        last_raw = ""
        last_err = ""
        warnings: list[str] = []

        for attempt in range(1, max_attempts + 1):
            try:
                resp = client.chat(
                    messages,
                    tools=None,
                    temperature=client.config.temperature,
                    response_format={"type": "json_object"},
                )
            except Exception as exc:  # noqa: BLE001
                return ExtractionResult(
                    ok=False,
                    skill_id=skill_id,
                    run_id=rid,
                    stop_reason="llm_error",
                    payload_schema=skill.payload_schema,
                    final_answer=f"LLM 调用失败: {exc}",
                    attempts=attempt,
                    steps=steps,
                )

            raw = _message_content(resp)
            last_raw = raw
            steps.append(
                {
                    "step": attempt,
                    "phase": "extract",
                    "ok": True,
                    "raw_chars": len(raw),
                }
            )

            try:
                parsed = parse_json_object(raw)
                parsed = apply_known_ids(parsed, text, known)
                # 已知键覆盖（显式传入优先）
                if known.get("customer_id"):
                    parsed["customer_id"] = known["customer_id"]
                if known.get("vin"):
                    parsed["vin"] = str(known["vin"]).upper()
                if known.get("channel") and skill.payload_schema == "ticket_draft_v1":
                    parsed["ticket_channel"] = known["channel"]

                payload, w = validate_payload(
                    skill.payload_schema,
                    parsed,
                    source_text=text,
                    allowed_tags=allowed_tags,
                    tag_meta=tag_meta,
                )
                warnings.extend(w)
                steps.append(
                    {
                        "step": attempt,
                        "phase": "validate",
                        "ok": True,
                        "warnings": w,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                last_err = format_validation_error(exc)
                steps.append(
                    {
                        "step": attempt,
                        "phase": "validate",
                        "ok": False,
                        "error": last_err,
                    }
                )
                if attempt >= max_attempts:
                    return ExtractionResult(
                        ok=False,
                        skill_id=skill_id,
                        run_id=rid,
                        stop_reason="schema_fail",
                        payload_schema=skill.payload_schema,
                        raw_model_output=last_raw,
                        final_answer=f"Schema 校验失败: {last_err}",
                        attempts=attempt,
                        warnings=warnings,
                        steps=steps,
                    )
                messages.append({"role": "assistant", "content": raw or ""})
                messages.append(
                    {
                        "role": "user",
                        "content": build_retry_message(last_err, last_raw),
                    }
                )
                continue

            # 成功路径：可选写共享产出
            do_write = skill.write_ai_output if write_output is None else write_output
            ai_output_id = None
            if do_write:
                ctx = ToolContext(
                    run_id=rid,
                    skill_id=skill_id,
                    agent_type="extraction",
                )
                result = self.registry.call(
                    "write_ai_output",
                    {
                        "producer_skill": skill_id,
                        "payload": payload,
                        "consumer_allow": list(skill.consumer_allow),
                        "payload_schema": skill.payload_schema,
                        "run_id": rid,
                    },
                    context=ctx,
                )
                steps.append(
                    {
                        "step": attempt,
                        "phase": "write_ai_output",
                        "ok": result.ok,
                        "error": result.error,
                        "error_code": result.error_code,
                    }
                )
                if not result.ok:
                    return ExtractionResult(
                        ok=False,
                        skill_id=skill_id,
                        run_id=rid,
                        stop_reason="write_fail",
                        payload_schema=skill.payload_schema,
                        payload=payload,
                        raw_model_output=last_raw,
                        final_answer=f"校验通过但写入失败: {result.error}",
                        attempts=attempt,
                        warnings=warnings,
                        steps=steps,
                    )
                ai_row = (result.data or {}).get("ai_output") or {}
                ai_output_id = ai_row.get("ai_output_id")

            summary = {
                "tag_id": payload.get("tag_id"),
                "sentiment": payload.get("sentiment"),
                "ai_output_id": ai_output_id,
            }
            return ExtractionResult(
                ok=True,
                skill_id=skill_id,
                run_id=rid,
                stop_reason="validated",
                payload_schema=skill.payload_schema,
                payload=payload,
                raw_model_output=last_raw,
                final_answer=json.dumps(summary, ensure_ascii=False),
                attempts=attempt,
                warnings=warnings,
                ai_output_id=ai_output_id,
                steps=steps,
            )

        return ExtractionResult(
            ok=False,
            skill_id=skill_id,
            run_id=rid,
            stop_reason="schema_fail",
            payload_schema=skill.payload_schema,
            raw_model_output=last_raw,
            final_answer=last_err or "未知失败",
            attempts=max_attempts,
            warnings=warnings,
            steps=steps,
        )


def run_extraction(
    skill_id: str,
    user_input: str | dict[str, Any],
    *,
    run_id: str | None = None,
    write_output: bool | None = None,
    llm: DeepSeekClient | None = None,
) -> ExtractionResult:
    return ExtractionAgent(llm=llm).run(
        skill_id, user_input, run_id=run_id, write_output=write_output
    )
