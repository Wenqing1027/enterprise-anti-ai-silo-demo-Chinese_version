"""ReAct 控制环：think → act → observe + 停止条件。"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from agents.react.prompts import build_system_prompt, build_user_message
from agents.react.security import (
    precheck_tool_args,
    precheck_tool_calls_count,
    sanitize_observation,
    should_stop_for_outreach,
)
from agents.react.skill_loader import load_skill
from agents.react.skill_schema import SkillConfig
from agents.react.tool_calls import (
    allows_empty_args,
    assistant_tool_call_message,
    extract_tool_calls,
    tool_result_message,
)
from shared.llm.client import DeepSeekClient, get_llm_client
from shared.tools.base import ToolContext
from shared.tools.registry import ToolRegistry, default_registry

# 成功条件满足后，额外允许的终答轮数（关闭 tools）
SUCCESS_FINAL_ROUNDS = 1


@dataclass
class ReactResult:
    ok: bool
    skill_id: str
    run_id: str
    final_answer: str
    stop_reason: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    success_flags: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "skill_id": self.skill_id,
            "run_id": self.run_id,
            "final_answer": self.final_answer,
            "stop_reason": self.stop_reason,
            "steps": self.steps,
            "success_flags": self.success_flags,
        }


def _openai_tools(registry: ToolRegistry, names: list[str]) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for name in names:
        spec = registry.get_spec(name)
        if not spec:
            continue
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.parameters,
                },
            }
        )
    return tools


class ReactAgent:
    def __init__(
        self,
        registry: ToolRegistry | None = None,
        llm: DeepSeekClient | None = None,
        *,
        max_steps: int = 8,
    ) -> None:
        self.registry = registry or default_registry
        self.llm = llm
        self.max_steps = max_steps

    def run(
        self,
        skill_id: str,
        user_input: str | dict[str, Any],
        *,
        run_id: str | None = None,
    ) -> ReactResult:
        skill = load_skill(skill_id)
        rid = run_id or f"react-{uuid.uuid4().hex[:10]}"
        allow = list(skill.allowed_tools) or list(
            self.registry.allowed_tools_for_skill(skill_id) or []
        )
        if not allow:
            return ReactResult(
                ok=False,
                skill_id=skill_id,
                run_id=rid,
                final_answer="Skill 未配置 allowed_tools",
                stop_reason="config_error",
            )

        text, known = self._normalize_input(user_input)
        max_steps = int(skill.max_steps or self.max_steps)
        system = build_system_prompt(skill, allow)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": build_user_message(skill_id, text, known=known)},
        ]
        tools = _openai_tools(self.registry, allow)
        kb_allow = list(skill.security.kb_domains_allow) or None
        ctx = ToolContext(
            run_id=rid,
            skill_id=skill_id,
            agent_type="react",
            kb_domains_allow=kb_allow,
        )

        steps: list[dict[str, Any]] = []
        flags: dict[str, Any] = {
            "wrote_ai_output": False,
            "ai_output_id": None,
            "master_lookup": False,
            "channel_lookup": False,
        }
        deny_streak = 0
        bad_args_streak = 0
        need_final_round = False

        client = self.llm or get_llm_client()

        # max_steps 只约束「带 tools 的工具轮」；成功后的 +1 终答轮在循环外单独执行，互不打架
        for step_i in range(1, max_steps + 1):
            try:
                resp = client.chat(messages, tools=tools, tool_choice="auto")
            except Exception as exc:  # noqa: BLE001
                return ReactResult(
                    ok=False,
                    skill_id=skill_id,
                    run_id=rid,
                    final_answer=f"LLM 调用失败: {exc}",
                    stop_reason="llm_error",
                    steps=steps,
                    success_flags=flags,
                )

            msg = resp.choices[0].message
            parsed_calls = extract_tool_calls(msg)

            if not parsed_calls:
                answer = (getattr(msg, "content", None) or "").strip()
                reason = "success" if self._success_met(skill, flags) else "final"
                return ReactResult(
                    ok=True,
                    skill_id=skill_id,
                    run_id=rid,
                    final_answer=answer or "（模型未返回文本）",
                    stop_reason=reason,
                    steps=steps,
                    success_flags=flags,
                )

            count_v = precheck_tool_calls_count(skill, len(parsed_calls))
            if not count_v.allow:
                return ReactResult(
                    ok=False,
                    skill_id=skill_id,
                    run_id=rid,
                    final_answer=count_v.message or "单步工具调用过多",
                    stop_reason="security_stop",
                    steps=steps,
                    success_flags=flags,
                )

            messages.append(
                assistant_tool_call_message(getattr(msg, "content", None), parsed_calls)
            )

            for call in parsed_calls:
                args = dict(call.arguments)
                parse_bad = "_raw" in args
                empty_bad = (not args) and (not allows_empty_args(call.name))
                if parse_bad or empty_bad:
                    bad_args_streak += 1
                else:
                    bad_args_streak = 0

                args = self._enrich_args(call.name, args, known, skill_id=skill_id)
                pre = precheck_tool_args(
                    skill,
                    call.name,
                    args,
                    fetcher=self.registry.fetcher,
                )
                if not pre.allow:
                    steps.append(
                        {
                            "step": step_i,
                            "tool": call.name,
                            "args": args,
                            "ok": False,
                            "error_code": pre.code,
                        }
                    )
                    messages.append(
                        tool_result_message(
                            call.id,
                            {
                                "ok": False,
                                "tool_name": call.name,
                                "error": pre.message,
                                "error_code": pre.code,
                            },
                        )
                    )
                    deny_streak += 1
                    if deny_streak >= 2:
                        return ReactResult(
                            ok=False,
                            skill_id=skill_id,
                            run_id=rid,
                            final_answer=pre.message or "安全预检连续失败，已停止。",
                            stop_reason="security_stop",
                            steps=steps,
                            success_flags=flags,
                        )
                    continue
                args = pre.args if pre.args is not None else args

                result = self.registry.call(call.name, args, context=ctx)
                steps.append(
                    {
                        "step": step_i,
                        "tool": call.name,
                        "args": args,
                        "ok": result.ok,
                        "error_code": result.error_code,
                    }
                )

                if result.error_code == "TOOL_NOT_ALLOWED":
                    deny_streak += 1
                else:
                    deny_streak = 0

                self._update_flags(flags, call.name, result)
                obs = sanitize_observation(result.to_dict(), skill)
                messages.append(tool_result_message(call.id, obs))

                outreach = should_stop_for_outreach(skill, call.name, result.data)
                if not outreach.allow:
                    return ReactResult(
                        ok=False,
                        skill_id=skill_id,
                        run_id=rid,
                        final_answer=outreach.message or "触达已阻断",
                        stop_reason="security_stop",
                        steps=steps,
                        success_flags={**flags, "outreach_blocked": True},
                    )

                if deny_streak >= 2:
                    return ReactResult(
                        ok=False,
                        skill_id=skill_id,
                        run_id=rid,
                        final_answer="连续越权调用工具，已停止。",
                        stop_reason="tool_denied",
                        steps=steps,
                        success_flags=flags,
                    )
                if bad_args_streak >= 2:
                    return ReactResult(
                        ok=False,
                        skill_id=skill_id,
                        run_id=rid,
                        final_answer="连续无效工具参数，已停止。",
                        stop_reason="bad_args",
                        steps=steps,
                        success_flags=flags,
                    )

            if self._success_met(skill, flags):
                need_final_round = True
                break

        if need_final_round and SUCCESS_FINAL_ROUNDS > 0:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "成功条件已满足（共享产出/查询已完成）。"
                        "请勿再调用工具，直接按终答格式给出最终答复。"
                    ),
                }
            )
            try:
                resp = client.chat(messages, tools=None, tool_choice="none")
            except Exception as exc:  # noqa: BLE001
                return ReactResult(
                    ok=True,
                    skill_id=skill_id,
                    run_id=rid,
                    final_answer=f"成功条件已满足，但终答轮 LLM 失败: {exc}",
                    stop_reason="success",
                    steps=steps,
                    success_flags=flags,
                )
            msg = resp.choices[0].message
            parsed_calls = extract_tool_calls(msg)
            answer = (getattr(msg, "content", None) or "").strip()
            if parsed_calls:
                return ReactResult(
                    ok=True,
                    skill_id=skill_id,
                    run_id=rid,
                    final_answer=answer
                    or "成功条件已满足，但模型在终答轮仍尝试调用工具，已强制停止。",
                    stop_reason="success_forced",
                    steps=steps,
                    success_flags=flags,
                )
            return ReactResult(
                ok=True,
                skill_id=skill_id,
                run_id=rid,
                final_answer=answer or "（模型未返回文本）",
                stop_reason="success",
                steps=steps,
                success_flags=flags,
            )

        return ReactResult(
            ok=self._success_met(skill, flags),
            skill_id=skill_id,
            run_id=rid,
            final_answer="已达最大工具步数，请根据已收集证据人工收尾。",
            stop_reason="max_steps",
            steps=steps,
            success_flags=flags,
        )

    @staticmethod
    def _normalize_input(
        user_input: str | dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        if isinstance(user_input, str):
            return user_input, {}
        payload = dict(user_input)
        if "input" in payload and isinstance(payload["input"], dict):
            payload = dict(payload["input"])
        text = str(
            payload.get("text")
            or payload.get("query")
            or json.dumps(payload, ensure_ascii=False)
        )
        known = {
            k: payload.get(k)
            for k in ("customer_id", "vin", "channel", "dealer_id", "order_id", "store_id")
            if payload.get(k)
        }
        if payload.get("payload") is not None:
            known["payload"] = payload["payload"]
        if payload.get("consumer_allow") is not None:
            known["consumer_allow"] = payload["consumer_allow"]
        return text, known

    def _enrich_args(
        self,
        name: str,
        args: dict[str, Any],
        known: dict[str, Any],
        *,
        skill_id: str,
    ) -> dict[str, Any]:
        out = {k: v for k, v in args.items() if k != "_raw"}
        spec = self.registry.get_spec(name)
        props = set((spec.parameters or {}).get("properties", {}).keys()) if spec else set()
        for key in ("customer_id", "vin", "dealer_id", "order_id", "store_id", "channel"):
            if key in known and key in props and not out.get(key):
                out[key] = known[key]
        if name == "write_ai_output":
            if not out.get("producer_skill"):
                out["producer_skill"] = skill_id
            if not out.get("payload") and known.get("payload") is not None:
                out["payload"] = known["payload"]
            if not out.get("consumer_allow") and known.get("consumer_allow") is not None:
                out["consumer_allow"] = known["consumer_allow"]
            if skill_id == "fill_ticket" and not out.get("consumer_allow"):
                out["consumer_allow"] = ["renewal_plan", "voc_tagging"]
            if skill_id == "shared_write" and not out.get("consumer_allow"):
                out["consumer_allow"] = ["renewal_plan"]
        return out

    @staticmethod
    def _update_flags(flags: dict[str, Any], name: str, result: Any) -> None:
        if not result.ok:
            return
        data = result.data or {}
        if name == "write_ai_output":
            flags["wrote_ai_output"] = True
            ai = data.get("ai_output") or {}
            flags["ai_output_id"] = ai.get("id") or ai.get("ai_output_id")
            payload = ai.get("payload") if isinstance(ai, dict) else None
            if isinstance(payload, dict):
                flags["payload_has_customer"] = bool(payload.get("customer_id"))
                flags["payload_has_tag"] = bool(payload.get("tag_id"))
        if name in {
            "get_customer",
            "get_vehicle",
            "get_order",
            "list_orders",
            "list_inventory",
        }:
            flags["master_lookup"] = True
        if name in {
            "get_dealer_health",
            "list_alerts",
            "list_sales_metrics",
            "list_inspections",
            "get_risk",
        }:
            flags["channel_lookup"] = True

    @staticmethod
    def _success_met(skill: SkillConfig, flags: dict[str, Any]) -> bool:
        rule = skill.success_when
        if rule == "none":
            return False
        if rule == "wrote_ai_output":
            return bool(flags.get("wrote_ai_output"))
        if rule == "master_lookup":
            return bool(flags.get("master_lookup"))
        if rule == "channel_lookup":
            return bool(flags.get("channel_lookup"))
        return False


def run_react(
    skill_id: str,
    user_input: str | dict[str, Any],
    *,
    run_id: str | None = None,
    registry: ToolRegistry | None = None,
) -> ReactResult:
    return ReactAgent(registry=registry).run(skill_id, user_input, run_id=run_id)
