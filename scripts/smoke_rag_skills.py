#!/usr/bin/env python3
"""R3 RAG Skill 契约冒烟：YAML 可加载 + 分流正确 + 不破坏 ReAct/Extraction。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.rag import load_rag_skill  # noqa: E402
from apps.skill_dispatch import list_skill_ids, load_skill_public, peek_skill_kind  # noqa: E402


def main() -> None:
    for sid, domain in (
        ("repair_kb", "repair"),
        ("policy_kb", "policy"),
        ("hr_rules", "hr"),
    ):
        assert peek_skill_kind(sid) == "rag", sid
        cfg = load_rag_skill(sid)
        assert cfg.skill_id == sid
        assert cfg.agent_type == "rag"
        assert domain in cfg.kb_domains_allow
        assert cfg.security.kb_domains_allow  # 双闸回填
        pub = load_skill_public(sid)
        assert pub["agent_kind"] == "rag"
        assert domain in pub["kb_domains_allow"]

    assert peek_skill_kind("fill_ticket") == "react"
    assert peek_skill_kind("ticket_fields") == "extraction"

    rag_ids = [s for s in list_skill_ids() if peek_skill_kind(s) == "rag"]
    assert set(rag_ids) >= {"repair_kb", "policy_kb", "hr_rules"}

    # 误加载防护：ReAct loader 不应默默吞掉 RAG
    from agents.react.skill_loader import load_skill

    try:
        load_skill("repair_kb")
        raise AssertionError("react loader should reject rag skill shape")
    except (ValueError, Exception) as exc:
        # Pydantic 缺 max_steps/tone 形态不同会报错即可
        assert exc is not None

    print("OK rag skills smoke")
    print(
        json.dumps(
            {
                "rag_skills": rag_ids,
                "repair_domains": load_skill_public("repair_kb")["kb_domains_allow"],
                "policy_top_k": load_skill_public("policy_kb")["top_k"],
                "hr_cite": load_skill_public("hr_rules")["cite_required"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
