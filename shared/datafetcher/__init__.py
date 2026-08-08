"""统一 DataFetcher：只读、统一模型、来源对上层透明。"""

from __future__ import annotations

from shared.datafetcher.fetcher import DataFetcher, default_fetcher
from shared.datafetcher.types import KbChunk

get_customer = default_fetcher.get_customer
get_vehicle = default_fetcher.get_vehicle
get_order = default_fetcher.get_order
get_ticket = default_fetcher.get_ticket
search_kb = default_fetcher.search_kb
list_capabilities = default_fetcher.list_capabilities
get_renewal = default_fetcher.get_renewal
list_tags = default_fetcher.list_tags

__all__ = [
    "DataFetcher",
    "default_fetcher",
    "KbChunk",
    "get_customer",
    "get_vehicle",
    "get_order",
    "get_ticket",
    "search_kb",
    "list_capabilities",
    "get_renewal",
    "list_tags",
]
