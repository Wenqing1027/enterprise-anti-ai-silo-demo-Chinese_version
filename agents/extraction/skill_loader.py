"""加载 skills/<id>/skill.yaml（Extraction）。"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from agents.extraction.skill_schema import ExtractionSkillConfig

ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = ROOT / "skills"


def load_extraction_skill(skill_id: str) -> ExtractionSkillConfig:
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
    # 拒绝误用 ReAct skill（缺 payload_schema）
    if "payload_schema" not in data:
        raise ValueError(
            f"{path} 缺少 payload_schema；Extraction Skill 须声明 "
            "ticket_draft_v1 或 voc_entities_v1"
        )
    try:
        return ExtractionSkillConfig.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"extraction skill.yaml schema error ({path}):\n{exc}") from exc
