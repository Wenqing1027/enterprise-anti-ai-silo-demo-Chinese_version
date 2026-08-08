#!/usr/bin/env python3
"""1.4 DataFetcher 冒烟：只读查询 + 统一模型 + 来源透明。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.datafetcher import DataFetcher, KbChunk  # noqa: E402
from shared.models import Customer, Order, Ticket, Vehicle  # noqa: E402


def main() -> None:
    seed = json.loads((ROOT / "data/seeds/story_1_fill_ticket.json").read_text(encoding="utf-8"))
    inp = seed["input"]

    fetcher = DataFetcher()

    # 禁止写接口：约定检查
    assert not hasattr(fetcher, "write_ai_output")
    assert not hasattr(fetcher, "save")
    assert not hasattr(fetcher, "upsert")

    customer = fetcher.get_customer(inp["customer_id"])
    vehicle = fetcher.get_vehicle(inp["vin"])
    ticket = fetcher.get_ticket(seed["fixture_ticket_id"])
    renewal = fetcher.get_renewal(inp["customer_id"], inp["vin"])

    assert isinstance(customer, Customer) and customer.customer_id == inp["customer_id"]
    assert isinstance(vehicle, Vehicle) and vehicle.vin == inp["vin"]
    assert ticket is None or isinstance(ticket, Ticket)

    orders = fetcher.list_orders(limit=3)
    assert orders and all(isinstance(o, Order) for o in orders)

    kb_hits = fetcher.search_kb("续航低于标称怎么排查", domain="repair", top_k=3)
    assert kb_hits and all(isinstance(h, KbChunk) for h in kb_hits)
    assert kb_hits[0].kb_score and kb_hits[0].kb_score > 0

    tags = fetcher.list_tags(domain="risk")
    assert any(t.tag_id == "TAG-投诉未结" for t in tags)

    caps = fetcher.list_capabilities()
    assert any(c.skill_id == "fill_ticket" for c in caps)

    # 返回值不应携带数据源路径字段
    dumped = customer.model_dump()
    assert "source" not in dumped and "path" not in dumped and "_source" not in dumped

    print("OK DataFetcher smoke")
    print(
        json.dumps(
            {
                "customer_id": customer.customer_id,
                "vin": vehicle.vin,
                "renew_pool": renewal.renew_pool_layer if renewal else None,
                "kb_top": {
                    "title": kb_hits[0].title,
                    "score": kb_hits[0].kb_score,
                    "domain": str(kb_hits[0].kb_domain),
                },
                "orders_sample": len(orders),
                "capabilities": len(caps),
                "sources_contract": fetcher.describe_sources()["contract"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
