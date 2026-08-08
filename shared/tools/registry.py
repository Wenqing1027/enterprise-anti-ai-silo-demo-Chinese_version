"""ToolRegistry：唯一工具注册与调用入口。"""

from __future__ import annotations

import inspect
from typing import Any

from shared.datafetcher.fetcher import DataFetcher, default_fetcher
from shared.store.store import SharedStore, default_store
from shared.tools.base import ToolContext, ToolError, ToolResult, ToolSpec
from shared.tools.governance import TOOL_CLASSES, classify_all, resolve_tool_class
from shared.tools.guards import validate_against_spec
from shared.tools.handlers import build_tool_specs


class ToolRegistry:
    """所有业务动作只在此注册一次；Agent/Skill 仅 call，不复制实现。"""

    def __init__(
        self,
        fetcher: DataFetcher | None = None,
        store: SharedStore | None = None,
        *,
        enforce_skill_allowlist: bool = True,
    ) -> None:
        self.fetcher = fetcher or default_fetcher
        self.store = store or default_store
        self.enforce_skill_allowlist = enforce_skill_allowlist
        self._tools: dict[str, ToolSpec] = {}
        for spec in build_tool_specs(self.fetcher, self.store):
            # 治理三类映射（不拆 handler；业务域仍在 category）
            spec.tool_class = resolve_tool_class(spec.name, spec.category)
            self.register(spec)

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"duplicate tool: {spec.name}")
        if not spec.tool_class or spec.tool_class not in TOOL_CLASSES:
            spec.tool_class = resolve_tool_class(spec.name, spec.category)
        self._tools[spec.name] = spec

    def list_tools(
        self,
        *,
        category: str | None = None,
        tool_class: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = []
        for spec in self._tools.values():
            if category and spec.category != category:
                continue
            if tool_class and spec.tool_class != tool_class:
                continue
            rows.append(
                {
                    "name": spec.name,
                    "description": spec.description,
                    "tool_class": spec.tool_class,
                    "category": spec.category,
                    "domain": spec.category,
                    "readonly": spec.readonly,
                    "parameters": spec.parameters,
                    "required": spec.required,
                }
            )
        rows.sort(key=lambda x: (x["tool_class"], x["category"], x["name"]))
        return rows

    def tool_class_summary(self) -> dict[str, Any]:
        rows = self.list_tools()
        by_class = classify_all(rows)
        return {
            "tool_classes": list(TOOL_CLASSES),
            "counts": {c: len(by_class[c]) for c in TOOL_CLASSES},
            "by_class": by_class,
            "total": len(rows),
        }

    def get_spec(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def allowed_tools_for_skill(self, skill_id: str) -> list[str] | None:
        cap = self.fetcher.get_capability(skill_id)
        if not cap or not cap.allowed_tools:
            return None
        return list(cap.allowed_tools)

    def call(
        self,
        name: str,
        args: dict[str, Any] | None = None,
        *,
        context: ToolContext | None = None,
    ) -> ToolResult:
        spec = self._tools.get(name)
        if not spec:
            return ToolResult(
                ok=False,
                tool_name=name,
                error=f"unknown tool: {name}",
                error_code="UNKNOWN_TOOL",
            )
        ctx = context or ToolContext()
        args = dict(args or {})

        try:
            self._assert_allowed(name, ctx)
            cleaned = validate_against_spec(spec, args)
            payload = self._invoke(spec, cleaned, ctx)
            return ToolResult(ok=True, tool_name=name, data=payload)
        except ToolError as exc:
            return ToolResult(
                ok=False,
                tool_name=name,
                error=exc.message,
                error_code=exc.code,
            )
        except Exception as exc:  # noqa: BLE001 - demo boundary
            return ToolResult(
                ok=False,
                tool_name=name,
                error=str(exc),
                error_code="INTERNAL_ERROR",
            )

    def _assert_allowed(self, name: str, ctx: ToolContext) -> None:
        if not self.enforce_skill_allowlist:
            return
        allow = ctx.allowed_tools
        if allow is None and ctx.skill_id:
            allow = self.allowed_tools_for_skill(ctx.skill_id)
        if allow is None:
            # 无 skill 上下文：允许调用（供冒烟/运维）；有 skill 则必须命中白名单
            if ctx.skill_id:
                raise ToolError(
                    f"skill {ctx.skill_id} has no allowed_tools configured",
                    code="SKILL_ALLOWLIST_MISSING",
                )
            return
        if name not in allow:
            raise ToolError(
                f"tool '{name}' not allowed for skill '{ctx.skill_id}'",
                code="TOOL_NOT_ALLOWED",
            )

    def _invoke(
        self,
        spec: ToolSpec,
        args: dict[str, Any],
        ctx: ToolContext,
    ) -> dict[str, Any]:
        fn = spec.handler
        kwargs = dict(args)
        # 仅当 handler 声明 _context 时注入，避免多余参数报错
        try:
            sig = inspect.signature(fn)
            if "_context" in sig.parameters:
                kwargs["_context"] = ctx
        except (TypeError, ValueError):
            pass
        result = fn(**kwargs)
        if not isinstance(result, dict):
            return {"result": result}
        return result


default_registry = ToolRegistry()
