"""Demo 级工具调用限制。"""

from __future__ import annotations

import json
from typing import Any

from shared.tools.base import ToolError, ToolSpec


MAX_STRING_LEN = 4000
MAX_PAYLOAD_BYTES = 32_000
MAX_LIST_LIMIT = 100
ALLOWED_KB_DOMAINS = frozenset({"repair", "policy", "hr", "product", "channel"})
BLOCKING_TAGS = frozenset({"TAG-投诉未结", "TAG-舆情风险", "TAG-安全隐患"})


def ensure_required(args: dict[str, Any], required: list[str], tool_name: str) -> None:
    missing = [k for k in required if args.get(k) in (None, "")]
    if missing:
        raise ToolError(
            f"{tool_name}: missing required args {missing}",
            code="MISSING_ARGS",
        )


def clamp_limit(limit: Any, default: int = 20) -> int:
    if limit is None:
        return default
    try:
        n = int(limit)
    except (TypeError, ValueError) as exc:
        raise ToolError("limit must be int", code="INVALID_ARGS") from exc
    if n < 1:
        raise ToolError("limit must be >= 1", code="INVALID_ARGS")
    return min(n, MAX_LIST_LIMIT)


def guard_vin(vin: str | None) -> str | None:
    if vin is None:
        return None
    vin = str(vin).strip().upper()
    if len(vin) != 17:
        raise ToolError("vin must be 17 chars", code="INVALID_VIN")
    # Demo 合成数据约束：仅允许 QS0 前缀，防止误用真实号段
    if not vin.startswith("QS0"):
        raise ToolError(
            "demo only accepts synthetic VIN prefix QS0",
            code="VIN_NOT_SYNTHETIC",
        )
    return vin


def guard_customer_id(customer_id: str | None) -> str | None:
    if customer_id is None:
        return None
    cid = str(customer_id).strip()
    if not cid.startswith("CUS-"):
        raise ToolError("customer_id must start with CUS-", code="INVALID_CUSTOMER_ID")
    return cid


def guard_kb_domain(domain: str | None) -> str | None:
    if domain is None:
        return None
    d = str(domain).strip().lower()
    if d not in ALLOWED_KB_DOMAINS:
        raise ToolError(
            f"kb domain must be one of {sorted(ALLOWED_KB_DOMAINS)}",
            code="INVALID_KB_DOMAIN",
        )
    return d


def guard_text(text: Any, *, field: str = "text") -> str:
    if text is None:
        raise ToolError(f"{field} is required", code="MISSING_ARGS")
    s = str(text).strip()
    if not s:
        raise ToolError(f"{field} is empty", code="INVALID_ARGS")
    if len(s) > MAX_STRING_LEN:
        raise ToolError(
            f"{field} exceeds {MAX_STRING_LEN} chars",
            code="TEXT_TOO_LONG",
        )
    return s


def guard_payload(payload: Any) -> dict[str, Any] | list[Any]:
    if payload is None:
        raise ToolError("payload is required", code="MISSING_ARGS")
    if not isinstance(payload, (dict, list)):
        raise ToolError("payload must be object or array", code="INVALID_PAYLOAD")
    raw = json.dumps(payload, ensure_ascii=False, default=str)
    if len(raw.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise ToolError("payload too large", code="PAYLOAD_TOO_LARGE")
    # 禁止明文手机号形态写入共享层
    if _contains_raw_phone(raw):
        raise ToolError(
            "payload must not contain raw phone numbers; use phone_masked only",
            code="PII_FORBIDDEN",
        )
    if _contains_secret_pattern(raw):
        raise ToolError(
            "payload must not contain API keys or secret material",
            code="SECRET_FORBIDDEN",
        )
    return payload


def _contains_raw_phone(text: str) -> bool:
    import re

    return re.search(r"(?<!\*)1[3-9]\d{9}(?!\*)", text) is not None


def _contains_secret_pattern(text: str) -> bool:
    import re

    return (
        re.search(
            r"(?i)(sk-[a-z0-9]{10,}|api[_-]?key\s*[:=]\s*\S+|deepseek_api_key\s*[:=]\s*\S+)",
            text,
        )
        is not None
    )


def dump_model(obj: Any) -> Any:
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, list):
        return [dump_model(x) for x in obj]
    return obj


def validate_against_spec(spec: ToolSpec, args: dict[str, Any]) -> dict[str, Any]:
    """按 parameters.properties 做轻量类型/未知字段检查。"""
    props = (spec.parameters or {}).get("properties") or {}
    additional = (spec.parameters or {}).get("additionalProperties", False)
    cleaned: dict[str, Any] = {}
    for key, value in args.items():
        if key not in props and not additional:
            raise ToolError(f"unknown arg: {key}", code="UNKNOWN_ARG")
        cleaned[key] = value
    ensure_required(cleaned, spec.required, spec.name)
    return cleaned
