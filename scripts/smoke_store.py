#!/usr/bin/env python3
"""1.3 SharedStore 冒烟：Story1 写入 → Story2 读取并判定阻断。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.store import SharedStore  # noqa: E402


def main() -> None:
    seed1 = json.loads((ROOT / "data/seeds/story_1_fill_ticket.json").read_text(encoding="utf-8"))
    seed2 = json.loads((ROOT / "data/seeds/story_2_renewal_block.json").read_text(encoding="utf-8"))

    store = SharedStore(runtime_dir=ROOT / "data/runtime", persist=True)
    store.clear_runtime()

    inp = seed1["input"]
    expect = seed1["expect_write_ai_output"]
    run_id = "smoke-story1"

    store.log_step(run_id=run_id, step_name="fill_ticket.start", detail={"skill": "fill_ticket"})
    out = store.write_ai_output(
        producer_skill=expect["producer_skill"],
        consumer_allow=expect["consumer_allow"],
        run_id=run_id,
        payload_schema="ticket_draft_v1",
        payload={
            "ticket_id": seed1["fixture_ticket_id"],
            "customer_id": inp["customer_id"],
            "vin": inp["vin"],
            "tag_id": "TAG-投诉未结",
            "sentiment": "neg",
            "desc_text": inp["text"],
            "channel": inp["channel"],
        },
    )
    store.log_step(
        run_id=run_id,
        step_name="write_ai_output",
        detail={"ai_output_id": out.ai_output_id},
    )

    # Story2：renewal_plan 消费共享产出
    rows = store.read_ai_outputs(
        consumer_skill="renewal_plan",
        customer_id=seed2["input"]["customer_id"],
        vin=seed2["input"]["vin"],
    )
    blocked, tags = store.has_blocking_tag(
        customer_id=seed2["input"]["customer_id"],
        vin=seed2["input"]["vin"],
        consumer_skill="renewal_plan",
    )

    assert out.ai_output_id
    assert len(rows) >= 1
    assert blocked is True
    assert any("投诉未结" in t for t in tags)
    assert store.stats()["ai_outputs"] >= 1

    print("OK SharedStore smoke")
    print(
        json.dumps(
            {
                "ai_output_id": out.ai_output_id,
                "read_count": len(rows),
                "blocked": blocked,
                "blocking_tags": tags,
                "stats": store.stats(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
