"""统一 Tools + ToolRegistry（业务动作唯一实现入口）。"""

from __future__ import annotations

from shared.tools.base import ToolContext, ToolError, ToolResult, ToolSpec
from shared.tools.governance import TOOL_CLASSES, resolve_tool_class
from shared.tools.registry import ToolRegistry, default_registry

call_tool = default_registry.call
list_tools = default_registry.list_tools

__all__ = [
    "ToolRegistry",
    "default_registry",
    "ToolContext",
    "ToolResult",
    "ToolSpec",
    "ToolError",
    "TOOL_CLASSES",
    "resolve_tool_class",
    "call_tool",
    "list_tools",
]

