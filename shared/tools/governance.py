"""平台工具治理三类（V2）· 映射表。

主治理轴（对外 / OpenAPI / 台账）：
  read | knowledge | write_govern

次级索引仍用 ToolSpec.category（业务域）：
  master | commerce | service | renewal | knowledge | shared | channel | iot …

不拆 handler 文件；本模块只做归类与展示。
"""

from __future__ import annotations

from typing import Any

TOOL_CLASSES: tuple[str, ...] = ("read", "knowledge", "write_govern")

TOOL_CLASS_META: dict[str, dict[str, Any]] = {
    "read": {
        "name": "Read（只读业务）",
        "blurb": "主数据 / 交易 / 服务 / 续费 / 渠道 / IoT 等只读查询与规则演算。",
    },
    "knowledge": {
        "name": "Knowledge（知识检索）",
        "blurb": "知识库检索与文档读取；Retrieve 环主用。",
    },
    "write_govern": {
        "name": "Write/Govern（写共享与治理）",
        "blurb": "写共享产出、读共享标签、触达闸门、能力目录、运行日志。",
    },
}

# 显式清单（优先于域启发式）
KNOWLEDGE_TOOLS: frozenset[str] = frozenset(
    {
        "search_kb",
        "get_kb_document",
        "list_kb_domains",
    }
)

WRITE_GOVERN_TOOLS: frozenset[str] = frozenset(
    {
        "write_ai_output",
        "read_ai_outputs",
        "read_shared_tags",
        "get_ai_output",
        "check_outreach_block",
        "list_capabilities",
        "get_capability",
        "log_step",
        "list_run_logs",
    }
)

# 业务域 category → 默认 tool_class（仅当工具名未命中显式清单时）
_DOMAIN_DEFAULT_CLASS: dict[str, str] = {
    "knowledge": "knowledge",
    "shared": "write_govern",
    "master": "read",
    "commerce": "read",
    "service": "read",
    "renewal": "read",
    "channel": "read",
    "iot": "read",
    "general": "read",
}


def resolve_tool_class(name: str, domain_category: str | None = None) -> str:
    """工具名 + 可选业务域 → 治理三类之一。"""
    if name in KNOWLEDGE_TOOLS:
        return "knowledge"
    if name in WRITE_GOVERN_TOOLS:
        return "write_govern"
    if domain_category:
        mapped = _DOMAIN_DEFAULT_CLASS.get(domain_category)
        if mapped:
            # shared 域里未列入 write_govern 的（如 get_tag）降为 read
            if domain_category == "shared" and name not in WRITE_GOVERN_TOOLS:
                return "read"
            return mapped
    return "read"


def classify_all(tool_rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    """按 tool_class 分组工具名（台账摘要）。"""
    out: dict[str, list[str]] = {c: [] for c in TOOL_CLASSES}
    for row in tool_rows:
        name = row.get("name") or ""
        tc = row.get("tool_class") or resolve_tool_class(name, row.get("category"))
        if tc not in out:
            out[tc] = []
        out[tc].append(name)
    for c in out:
        out[c].sort()
    return out


def meta_payload() -> dict[str, Any]:
    """供 /v1/meta 挂载。"""
    return {
        "tool_classes": list(TOOL_CLASSES),
        "tool_class_meta": {
            k: {"name": v["name"], "blurb": v["blurb"]} for k, v in TOOL_CLASS_META.items()
        },
    }


def ledger_snapshot() -> dict[str, Any]:
    """机读台账快照（写入 JSON 或 API）。"""
    return {
        "version": "v2",
        "tool_classes": list(TOOL_CLASSES),
        "knowledge_tools": sorted(KNOWLEDGE_TOOLS),
        "write_govern_tools": sorted(WRITE_GOVERN_TOOLS),
        "note": "未列入上两表的工具默认 tool_class=read；业务域见 ToolSpec.category。",
    }
