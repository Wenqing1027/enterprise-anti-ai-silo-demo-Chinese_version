"""共享 Store：Agent 动态产出（AIOutput / RunLog / 共享标签视图）。"""

from __future__ import annotations

from shared.store.store import SharedStore, default_store

write_ai_output = default_store.write_ai_output
read_ai_outputs = default_store.read_ai_outputs
get_ai_output = default_store.get_ai_output
read_shared_tags = default_store.read_shared_tags
has_blocking_tag = default_store.has_blocking_tag
log_step = default_store.log_step
list_run_logs = default_store.list_run_logs
clear_runtime = default_store.clear_runtime

__all__ = [
    "SharedStore",
    "default_store",
    "write_ai_output",
    "read_ai_outputs",
    "get_ai_output",
    "read_shared_tags",
    "has_blocking_tag",
    "log_step",
    "list_run_logs",
    "clear_runtime",
]
