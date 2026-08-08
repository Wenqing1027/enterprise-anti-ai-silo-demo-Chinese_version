"""Tool 基础类型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolContext:
    """一次调用的上下文（用于权限与审计限制）。"""

    run_id: str | None = None
    skill_id: str | None = None
    agent_type: str | None = None
    # 若设置，则优先于 capability_catalog 白名单
    allowed_tools: list[str] | None = None
    # Skill.security.kb_domains_allow；非空时知识库工具必须落在该域
    kb_domains_allow: list[str] | None = None


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., dict[str, Any]]
    readonly: bool = True
    # 业务域次级标签（master/commerce/service/…）；主治理轴见 tool_class
    category: str = "general"
    required: list[str] = field(default_factory=list)
    # 平台治理三类：read | knowledge | write_govern
    tool_class: str = "read"


@dataclass
class ToolResult:
    ok: bool
    tool_name: str
    data: Any = None
    error: str | None = None
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "tool_name": self.tool_name,
            "data": self.data,
            "error": self.error,
            "error_code": self.error_code,
        }


class ToolError(Exception):
    def __init__(self, message: str, code: str = "TOOL_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code
