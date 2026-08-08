"""统一 RunResult 契约（阶段 D）。

公共字段（前端主认）：
  run_id · control_loop · skill_id · ok · final_text · steps[] · ai_output_ids[] · error

分环扩展（顶层，按环出现）：
  extract → payload
  retrieve → citations
  plan → gate { blocked, reason, tag_ids, allow_outreach? }

其余环内字段一律进 extensions（含 stop_reason / feature_id / success_flags / plan …）。

兼容：仍回传 final_answer = final_text（旧客户端过渡用，勿新写依赖）。
"""

from __future__ import annotations

from typing import Any

from apps.loops import PLATFORM_LOOPS, canonicalize

RUN_RESULT_VERSION = "2026.08.07-d"

COMMON_KEYS = (
    "run_id",
    "control_loop",
    "skill_id",
    "ok",
    "final_text",
    "steps",
    "ai_output_ids",
    "error",
)


def _as_list(v: Any) -> list[Any]:
    if v is None:
        return []
    if isinstance(v, list):
        return list(v)
    return [v]


def _collect_ai_output_ids(raw: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for x in _as_list(raw.get("ai_output_ids")):
        if x and str(x) not in ids:
            ids.append(str(x))
    one = raw.get("ai_output_id")
    if one and str(one) not in ids:
        ids.append(str(one))
    flags = raw.get("success_flags") or {}
    if isinstance(flags, dict):
        fid = flags.get("ai_output_id")
        if fid and str(fid) not in ids:
            ids.append(str(fid))
    return ids


def _normalize_gate(raw_gate: dict[str, Any] | None) -> dict[str, Any]:
    g = dict(raw_gate or {})
    tag_ids = _as_list(g.get("tag_ids") or g.get("blocking_tags"))
    tag_ids = [str(t) for t in tag_ids if t]
    return {
        "blocked": g.get("blocked"),
        "reason": g.get("reason") or g.get("block_reason"),
        "tag_ids": tag_ids,
        "allow_outreach": g.get("allow_outreach"),
        "blocking_tags": [str(t) for t in _as_list(g.get("blocking_tags")) if t],
    }


def wrap_run_result(
    raw: dict[str, Any],
    *,
    control_loop: str,
    feature_id: str | None = None,
    department_id: str | None = None,
    layout: str | None = None,
    tone_label: str | None = None,
    department_name: str | None = None,
    extra_extensions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """把各环原始 to_dict + 路由装饰字段，收成统一 RunResult。"""
    loop = canonicalize(control_loop) or str(control_loop)
    if loop not in PLATFORM_LOOPS:
        # 容错：未知环仍包装，但标在 extensions
        pass

    final_text = str(raw.get("final_text") or raw.get("final_answer") or "")
    ok = bool(raw.get("ok"))
    error = raw.get("error")
    if error is None and not ok:
        error = raw.get("stop_reason") or (final_text[:200] if final_text else "run_failed")

    out: dict[str, Any] = {
        "run_result_version": RUN_RESULT_VERSION,
        "run_id": raw.get("run_id"),
        "control_loop": loop if loop in PLATFORM_LOOPS else loop,
        "skill_id": raw.get("skill_id"),
        "ok": ok,
        "final_text": final_text,
        "steps": list(raw.get("steps") or []),
        "ai_output_ids": _collect_ai_output_ids(raw),
        "error": error if not ok else (raw.get("error") or None),
        # 过渡别名
        "final_answer": final_text,
    }

    if loop == "extract":
        out["payload"] = raw.get("payload")
    elif loop == "retrieve":
        out["citations"] = list(raw.get("citations") or [])
    elif loop == "plan":
        out["gate"] = _normalize_gate(raw.get("gate") if isinstance(raw.get("gate"), dict) else {})

    skip = {
        "run_id",
        "control_loop",
        "skill_id",
        "ok",
        "final_text",
        "final_answer",
        "steps",
        "ai_output_ids",
        "ai_output_id",
        "error",
        "payload",
        "citations",
        "gate",
        "run_result_version",
        "feature_id",
        "department_id",
        "layout",
        "tone_label",
        "department_name",
        "api_path",
        "agent_type_legacy",
        "resolved_via",
        "legacy_api_path",
        "extensions",
    }
    extensions: dict[str, Any] = {}
    for k, v in raw.items():
        if k in skip:
            continue
        extensions[k] = v

    if feature_id is not None or raw.get("feature_id") is not None:
        extensions["feature_id"] = feature_id if feature_id is not None else raw.get("feature_id")
    if department_id is not None or raw.get("department_id") is not None:
        extensions["department_id"] = (
            department_id if department_id is not None else raw.get("department_id")
        )
    if layout is not None or raw.get("layout") is not None:
        extensions["layout"] = layout if layout is not None else raw.get("layout")
    if tone_label is not None or raw.get("tone_label") is not None:
        extensions["tone_label"] = tone_label if tone_label is not None else raw.get("tone_label")
    if department_name is not None or raw.get("department_name") is not None:
        extensions["department_name"] = (
            department_name if department_name is not None else raw.get("department_name")
        )

    for k in ("api_path", "agent_type_legacy", "resolved_via", "legacy_api_path"):
        if raw.get(k) is not None:
            extensions[k] = raw[k]

    if extra_extensions:
        extensions.update(extra_extensions)

    # 单 id 也放进 extensions 便于旧逻辑
    if raw.get("ai_output_id"):
        extensions.setdefault("ai_output_id", raw.get("ai_output_id"))

    out["extensions"] = extensions
    return out


def assert_run_result_shape(body: dict[str, Any], *, expect_loop: str | None = None) -> list[str]:
    """冒烟用：返回缺失/违规说明（空列表=通过）。"""
    errs: list[str] = []
    for k in COMMON_KEYS:
        if k not in body:
            errs.append(f"missing:{k}")
    if not isinstance(body.get("steps"), list):
        errs.append("steps:not_list")
    if not isinstance(body.get("ai_output_ids"), list):
        errs.append("ai_output_ids:not_list")
    if "extensions" not in body or not isinstance(body.get("extensions"), dict):
        errs.append("extensions:missing_or_not_dict")
    loop = body.get("control_loop")
    if expect_loop and canonicalize(loop) != canonicalize(expect_loop):
        errs.append(f"control_loop:{loop}!=expected:{expect_loop}")
    if loop == "extract" and "payload" not in body:
        errs.append("extract:missing_payload")
    if loop == "retrieve" and "citations" not in body:
        errs.append("retrieve:missing_citations")
    if loop == "plan":
        gate = body.get("gate")
        if not isinstance(gate, dict):
            errs.append("plan:missing_gate")
        else:
            for gk in ("blocked", "reason", "tag_ids"):
                if gk not in gate:
                    errs.append(f"plan.gate.missing:{gk}")
    return errs
