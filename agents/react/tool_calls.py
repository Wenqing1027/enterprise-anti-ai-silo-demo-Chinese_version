"""DeepSeek / OpenAI 兼容 tool_calls 解析契约。

线格式（chat.completions）：
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": str | null,
      "tool_calls": [                 # 可空；空则视为终答
        {
          "id": "call_xxx",
          "type": "function",
          "function": {
            "name": "get_customer",
            "arguments": "{\"customer_id\":\"CUS-1\"}"  # JSON 字符串
          }
        }
      ]
    }
  }]
}

回写 messages 时：
- assistant：必须带同样结构的 tool_calls（arguments 保持字符串）
- tool：{"role":"tool","tool_call_id": id, "content": observation_json_str}
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ParsedToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    arguments_raw: str


def parse_arguments(raw: Any) -> tuple[dict[str, Any], str, bool]:
    """返回 (args_dict, raw_str, ok)。

    ok=False：无法解析为 object（记坏参）。
    """
    if raw is None:
        return {}, "{}", True
    if isinstance(raw, dict):
        return dict(raw), json.dumps(raw, ensure_ascii=False), True
    if not isinstance(raw, str):
        raw = str(raw)
    text = raw.strip() or "{}"
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {"_raw": text}, text, False
    if isinstance(data, dict):
        return data, text, True
    return {"_raw": text}, text, False


def extract_tool_calls(message: Any) -> list[ParsedToolCall]:
    """从 OpenAI SDK message 或 dict 提取 tool_calls。"""
    raw_calls = getattr(message, "tool_calls", None)
    if raw_calls is None and isinstance(message, dict):
        raw_calls = message.get("tool_calls")
    if not raw_calls:
        return []

    out: list[ParsedToolCall] = []
    for i, tc in enumerate(raw_calls):
        if isinstance(tc, dict):
            tc_id = str(tc.get("id") or f"call_auto_{i}")
            fn = tc.get("function") or {}
            name = str(fn.get("name") or "")
            args_raw = fn.get("arguments")
        else:
            tc_id = str(getattr(tc, "id", None) or f"call_auto_{i}")
            fn = getattr(tc, "function", None)
            name = str(getattr(fn, "name", None) or "")
            args_raw = getattr(fn, "arguments", None) if fn is not None else None
        args, raw_str, _ok = parse_arguments(args_raw)
        if not name:
            continue
        out.append(
            ParsedToolCall(
                id=tc_id,
                name=name,
                arguments=args,
                arguments_raw=raw_str,
            )
        )
    return out


def assistant_tool_call_message(
    content: str | None, calls: list[ParsedToolCall]
) -> dict[str, Any]:
    """构造可回灌 DeepSeek 的 assistant tool_calls 消息。"""
    return {
        "role": "assistant",
        "content": content or "",
        "tool_calls": [
            {
                "id": c.id,
                "type": "function",
                "function": {
                    "name": c.name,
                    "arguments": c.arguments_raw,
                },
            }
            for c in calls
        ],
    }


def tool_result_message(call_id: str, observation: dict[str, Any], *, limit: int = 8000) -> dict[str, Any]:
    body = json.dumps(observation, ensure_ascii=False, default=str)
    if len(body) > limit:
        body = body[:limit] + "…"
    return {
        "role": "tool",
        "tool_call_id": call_id,
        "content": body,
    }


def allows_empty_args(tool_name: str) -> bool:
    """无参合法的 list_* / 目录类工具。"""
    if tool_name.startswith("list_"):
        return True
    return tool_name in {"list_capabilities"}
