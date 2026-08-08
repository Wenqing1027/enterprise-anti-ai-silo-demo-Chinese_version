"""Extraction 冒烟：加载配置 → 跑 ticket_fields / voc_entities。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)


def _must(ok: bool, msg: str) -> None:
    status = "OK" if ok else "FAIL"
    print(f"[{status}] {msg}")
    if not ok:
        raise SystemExit(1)


def main() -> None:
    from shared.llm.client import load_llm_config
    from agents.extraction.agent import run_extraction

    cfg = load_llm_config(profile="extraction")
    _must(bool(cfg.api_key), "extraction LLM key 已加载")
    print(f"model={cfg.model} temperature={cfg.temperature} base={cfg.base_url}")

    ticket_seed = json.loads(
        (ROOT / "data/seeds/story_1_ticket_fields.json").read_text(encoding="utf-8")
    )
    r1 = run_extraction("ticket_fields", ticket_seed)
    _must(r1.ok, f"ticket_fields stop={r1.stop_reason}")
    _must(r1.payload is not None and "tag_id" in r1.payload, "ticket payload 含 tag_id")
    _must(bool(r1.ai_output_id), f"ticket 已写 AIOutput id={r1.ai_output_id}")
    print("ticket payload:", json.dumps(r1.payload, ensure_ascii=False))

    voc_seed = json.loads(
        (ROOT / "data/seeds/story_1_voc_entities.json").read_text(encoding="utf-8")
    )
    r2 = run_extraction("voc_entities", voc_seed)
    _must(r2.ok, f"voc_entities stop={r2.stop_reason}")
    _must(r2.payload is not None and "sentiment" in r2.payload, "voc payload 含 sentiment")
    tags = {r2.payload.get("tag_id"), *(r2.payload.get("secondary_tag_ids") or [])}
    blocking = {"TAG-投诉未结", "TAG-舆情风险", "TAG-安全隐患"}
    _must(bool(tags & blocking), f"阻断标签命中 tags={tags}")
    _must(bool(r2.ai_output_id), f"voc 已写 AIOutput id={r2.ai_output_id}")
    print("voc payload:", json.dumps(r2.payload, ensure_ascii=False))
    print("smoke_extraction: ALL PASS")


if __name__ == "__main__":
    main()
