"""按 YAML 形状分流加载 React / Extraction / RAG / Planning Skill。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml

from agents.extraction.skill_loader import load_extraction_skill
from agents.extraction.skill_schema import ExtractionSkillConfig
from agents.planning.skill_loader import load_planning_skill
from agents.planning.skill_schema import PlanningSkillConfig
from agents.rag.skill_loader import load_rag_skill
from agents.rag.skill_schema import RagSkillConfig
from agents.react.skill_loader import SKILLS_DIR, list_skill_ids, load_skill
from agents.react.skill_schema import SkillConfig
from apps.loops import to_legacy
from apps.skill_loops import resolve_skill_control_loop

AgentKind = Literal["react", "extraction", "rag", "planning"]


def peek_skill_kind(skill_id: str) -> AgentKind:
    path = SKILLS_DIR / skill_id / "skill.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"skill not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"invalid skill yaml: {path}")
    if data.get("payload_schema"):
        return "extraction"
    if data.get("control_loop") == "retrieve" or data.get("agent_type") == "rag":
        return "rag"
    if data.get("control_loop") == "plan" or data.get("agent_type") == "planning":
        return "planning"
    return "react"


def load_skill_public(skill_id: str) -> dict[str, Any]:
    """API / 目录用的统一公开视图。"""
    kind = peek_skill_kind(skill_id)
    if kind == "extraction":
        cfg: ExtractionSkillConfig = load_extraction_skill(skill_id)
        loop = resolve_skill_control_loop(
            skill_id=cfg.skill_id,
            declared=getattr(cfg, "control_loop", None),
            agent_kind="extraction",
        )
        return {
            "skill_id": cfg.skill_id,
            "control_loop": loop,
            "agent_kind": "extraction",
            "agent_type_legacy": to_legacy(loop),
            "department": cfg.department,
            "goal": cfg.goal,
            "success_hint": cfg.success_hint,
            "tone_label": cfg.tone.label,
            "tone": cfg.tone.model_dump(),
            "payload_schema": cfg.payload_schema,
            "write_ai_output": cfg.write_ai_output,
            "consumer_allow": list(cfg.consumer_allow),
            "allowed_tools": ["write_ai_output"] if cfg.write_ai_output else [],
            "success_when": "wrote_ai_output" if cfg.write_ai_output else "validated",
            "security": cfg.security.model_dump(),
        }
    if kind == "rag":
        cfg_rag: RagSkillConfig = load_rag_skill(skill_id)
        loop = resolve_skill_control_loop(
            skill_id=cfg_rag.skill_id,
            declared=getattr(cfg_rag, "control_loop", None),
            agent_kind="rag",
        )
        return {
            "skill_id": cfg_rag.skill_id,
            "control_loop": loop,
            "agent_kind": "rag",
            "agent_type": "rag",
            "agent_type_legacy": to_legacy(loop),
            "department": cfg_rag.department,
            "goal": cfg_rag.goal,
            "success_hint": cfg_rag.success_hint,
            "tone_label": cfg_rag.tone.label,
            "tone": cfg_rag.tone.model_dump(),
            "kb_domains_allow": list(cfg_rag.kb_domains_allow),
            "top_k": cfg_rag.top_k,
            "max_context_chars": cfg_rag.max_context_chars,
            "cite_required": cfg_rag.cite_required,
            "allowed_tools": list(cfg_rag.allowed_tools),
            "success_when": cfg_rag.success_when,
            "security": cfg_rag.security.model_dump(),
            "output_format": cfg_rag.output_format,
            "write_ai_output": cfg_rag.write_ai_output,
        }
    if kind == "planning":
        cfg_p: PlanningSkillConfig = load_planning_skill(skill_id)
        loop = resolve_skill_control_loop(
            skill_id=cfg_p.skill_id,
            declared=getattr(cfg_p, "control_loop", None),
            agent_kind="planning",
        )
        return {
            "skill_id": cfg_p.skill_id,
            "control_loop": loop,
            "agent_kind": "planning",
            "agent_type": "planning",
            "agent_type_legacy": to_legacy(loop),
            "department": cfg_p.department,
            "goal": cfg_p.goal,
            "success_hint": cfg_p.success_hint,
            "tone_label": cfg_p.tone.label,
            "tone": cfg_p.tone.model_dump(),
            "allowed_tools": list(cfg_p.allowed_tools),
            "success_when": cfg_p.success_when,
            "output_format": cfg_p.output_format,
            "flow_ids": list(cfg_p.flow_ids),
            "consumes_from": list(cfg_p.consumes_from),
        }
    cfg_r: SkillConfig = load_skill(skill_id)
    loop = resolve_skill_control_loop(
        skill_id=cfg_r.skill_id,
        declared=getattr(cfg_r, "control_loop", None),
        agent_kind="react",
    )
    return {
        "skill_id": cfg_r.skill_id,
        "control_loop": loop,
        "agent_kind": "react",
        "agent_type_legacy": to_legacy(loop),
        "department": cfg_r.department,
        "goal": cfg_r.goal,
        "success_hint": cfg_r.success_hint,
        "tone_label": cfg_r.tone.label,
        "tone": cfg_r.tone.model_dump(),
        "allowed_tools": list(cfg_r.allowed_tools),
        "success_when": cfg_r.success_when,
        "security": cfg_r.security.model_dump(),
        "output_format": cfg_r.output_format,
    }


__all__ = [
    "AgentKind",
    "list_skill_ids",
    "load_skill_public",
    "peek_skill_kind",
]
