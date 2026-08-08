"""加载 skills/<id>/skill.yaml（RAG）。"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from agents.rag.skill_schema import RagSkillConfig

ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = ROOT / "skills"


def load_rag_skill(skill_id: str) -> RagSkillConfig:
    path = SKILLS_DIR / skill_id / "skill.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"skill not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"invalid skill yaml (not a mapping): {path}")
    data.setdefault("skill_id", skill_id)
    if data.get("skill_id") != skill_id:
        raise ValueError(
            f"skill_id mismatch: dir={skill_id} yaml={data.get('skill_id')}"
        )
    if data.get("agent_type") != "rag" and "kb_domains_allow" not in data:
        raise ValueError(
            f"{path} 不是 RAG Skill：须 agent_type: rag 且声明 kb_domains_allow"
        )
    data.setdefault("agent_type", "rag")
    # 拒绝误把 Extraction / 纯 ReAct 当 RAG
    if data.get("payload_schema"):
        raise ValueError(f"{path} 含 payload_schema，应走 Extraction loader")
    try:
        return RagSkillConfig.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"rag skill.yaml schema error ({path}):\n{exc}") from exc
