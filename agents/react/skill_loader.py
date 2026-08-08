"""加载并校验 skills/<id>/skill.yaml。"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from agents.react.skill_schema import SkillConfig

ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = ROOT / "skills"


def load_skill(skill_id: str) -> SkillConfig:
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
    try:
        return SkillConfig.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"skill.yaml schema error ({path}):\n{exc}") from exc


def list_skill_ids() -> list[str]:
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(
        p.name for p in SKILLS_DIR.iterdir() if (p / "skill.yaml").is_file()
    )
