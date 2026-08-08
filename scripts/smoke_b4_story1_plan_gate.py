#!/usr/bin/env python3
"""B4 冒烟：先单独跑 Story1 写出投诉标签 → 再单独跑 Plan → 必须阻断触达。

两次独立运行，经共享层衔接；不联跑、不话筒接力。
默认 Story1 路径：Act · fill_ticket；可用 --via extract 走 ticket_fields。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# 避免本机 IDE 代理劫持 LLM
for _k in (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "SOCKS_PROXY",
    "SOCKS5_PROXY",
    "socks_proxy",
    "socks5_proxy",
):
    os.environ.pop(_k, None)

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

BLOCKING = {"TAG-投诉未结", "TAG-舆情风险", "TAG-安全隐患"}


def _ok(name: str, cond: bool, detail: str = "") -> None:
    print(f"[{'OK' if cond else 'FAIL'}] {name}" + (f" · {detail}" if detail else ""))
    if not cond:
        raise SystemExit(1)


def _run_story1_act(seed: dict) -> dict:
    from agents.react.agent import run_react

    rid = "b4-story1-fill-ticket"
    result = run_react("fill_ticket", seed.get("input") or seed, run_id=rid)
    data = result.to_dict()
    flags = data.get("success_flags") or {}
    ai_id = flags.get("ai_output_id")
    _ok("story1.act.ok", result.ok, f"stop={result.stop_reason}")
    _ok(
        "story1.act.wrote_shared",
        bool(flags.get("wrote_ai_output")) and bool(ai_id),
        f"stop={result.stop_reason} ai_output_id={ai_id} flags={flags}",
    )
    _ok(
        "story1.act.payload_has_tag",
        bool(flags.get("payload_has_tag")),
        str(flags),
    )
    return {
        "via": "act",
        "skill_id": "fill_ticket",
        "run_id": data.get("run_id") or rid,
        "stop_reason": result.stop_reason,
        "ai_output_id": ai_id,
        "ok": result.ok,
    }

def _run_story1_extract(seed: dict) -> dict:
    from agents.extraction.agent import run_extraction

    rid = "b4-story1-ticket-fields"
    result = run_extraction("ticket_fields", seed, run_id=rid)
    _ok("story1.extract.ok", result.ok, f"stop={result.stop_reason}")
    tag = (result.payload or {}).get("tag_id")
    _ok("story1.extract.tag", bool(tag), str(tag))
    _ok("story1.extract.wrote", bool(result.ai_output_id), str(result.ai_output_id))
    return {
        "via": "extract",
        "skill_id": "ticket_fields",
        "run_id": result.run_id,
        "stop_reason": result.stop_reason,
        "ai_output_id": result.ai_output_id,
        "tag_id": tag,
        "ok": result.ok,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="B4 Story1→Plan 阻断冒烟")
    parser.add_argument(
        "--via",
        choices=("act", "extract"),
        default="act",
        help="Story1 路径：act=fill_ticket（默认）· extract=ticket_fields",
    )
    args = parser.parse_args()

    from agents.planning.agent import run_planning
    from shared.store.store import default_store
    from shared.tools.guards import BLOCKING_TAGS

    seed_act = json.loads((ROOT / "data/seeds/story_1_fill_ticket.json").read_text(encoding="utf-8"))
    seed_ext = json.loads(
        (ROOT / "data/seeds/story_1_ticket_fields.json").read_text(encoding="utf-8")
    )
    seed2 = json.loads((ROOT / "data/seeds/story_2_renewal_block.json").read_text(encoding="utf-8"))
    cid = seed2["input"]["customer_id"]
    vin = seed2["input"]["vin"]
    # 与 Story1 seed 对齐
    _ok("seed.customer_aligned", seed_act["input"]["customer_id"] == cid)

    print("======== B4 · Story1 独立写出 → Plan 独立阻断 ========")
    default_store.clear_runtime()
    _ok("runtime.cleared", True)

    print(f"--- ① Story1 单独跑（via={args.via}）---")
    if args.via == "act":
        story1 = _run_story1_act(seed_act)
    else:
        story1 = _run_story1_extract(seed_ext)

    # 读共享层：必须出现阻断类标签（Story1 写出，供 renewal_plan 消费）
    tag_rows = default_store.read_shared_tags(
        consumer_skill="renewal_plan", customer_id=cid, vin=vin
    )
    tag_ids = [str(r.get("tag_id")) for r in tag_rows if r.get("tag_id")]
    outputs = default_store.read_ai_outputs(
        consumer_skill="renewal_plan", customer_id=cid, vin=vin, limit=20
    )
    for o in outputs:
        payload = o.payload or {}
        if payload.get("tag_id"):
            tag_ids.append(str(payload["tag_id"]))
        for t in payload.get("tags") or []:
            tag_ids.append(str(t))

    all_tags = set(tag_ids)
    if story1.get("tag_id"):
        all_tags.add(str(story1["tag_id"]))
    hit = all_tags & (set(BLOCKING_TAGS) | BLOCKING)
    _ok(
        "story1.shared.has_blocking_tag",
        bool(hit),
        f"tags={sorted(all_tags)} hit={sorted(hit)}",
    )

    print("--- ② Plan Skill 单独跑（renewal_plan）---")
    plan = run_planning(
        "renewal_plan",
        {"customer_id": cid, "vin": vin},
        run_id="b4-plan-renewal",
    )
    _ok("plan.ok", plan.ok, plan.stop_reason)
    _ok("plan.stop=blocked", plan.stop_reason == "blocked", plan.stop_reason)
    _ok("plan.gate.blocked", plan.gate.get("blocked") is True, str(plan.gate))
    _ok(
        "plan.allow_outreach=false",
        plan.gate.get("allow_outreach") is False,
        str(plan.gate),
    )
    reason = plan.gate.get("reason") or ""
    _ok(
        "plan.reason.complaint",
        "投诉" in reason or "TAG-投诉未结" in str(plan.gate) or bool(hit & all_tags),
        reason,
    )
    _ok("plan.action=block", (plan.plan or {}).get("action") == "block_outreach")
    _ok(
        "plan.independent_run",
        plan.run_id != story1["run_id"],
        f"story1={story1['run_id']} plan={plan.run_id}",
    )

    print(
        json.dumps(
            {
                "verdict": "B4 PASS · Story1 写出投诉标签后 Plan 独立阻断触达",
                "story1": story1,
                "shared_tags": sorted(all_tags),
                "blocking_hit": sorted(hit),
                "plan": {
                    "run_id": plan.run_id,
                    "stop_reason": plan.stop_reason,
                    "gate": plan.gate,
                    "plan_action": (plan.plan or {}).get("action"),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
