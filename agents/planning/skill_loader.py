"""加载 skills/<id>/skill.yaml（Planning）。"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from agents.planning.skill_schema import PlanningSkillConfig

ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = ROOT / "skills"


def load_planning_skill(skill_id: str) -> PlanningSkillConfig:
    path = SKILLS_DIR / skill_id / "skill.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"skill not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"invalid skill yaml (not a mapping): {path}")
    data.setdefault("skill_id", skill_id)
    data.setdefault("control_loop", "plan")
    data.setdefault("agent_type", "planning")
    if data.get("skill_id") != skill_id:
        raise ValueError(
            f"skill_id mismatch: dir={skill_id} yaml={data.get('skill_id')}"
        )
    if data.get("control_loop") not in (None, "plan") and data.get("agent_type") != "planning":
        raise ValueError(f"{path} 不是 Planning Skill：须 control_loop: plan")
    if data.get("payload_schema"):
        raise ValueError(f"{path} 含 payload_schema，应属 Extraction，不是 Planning")
    if data.get("kb_domains_allow") and data.get("control_loop") != "plan":
        raise ValueError(f"{path} 含 kb_domains_allow，更像 Retrieve Skill")
    try:
        return PlanningSkillConfig.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"planning skill.yaml schema error ({path}):\n{exc}") from exc
