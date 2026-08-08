"""Planning Skill 契约。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class PlanningTone(BaseModel):
    label: str = Field(..., min_length=1)
    style: str = Field(..., min_length=1)
    forbid: str = Field(default="")


class PlanningSkillConfig(BaseModel):
    skill_id: str = Field(..., min_length=1)
    control_loop: Literal["plan"] = "plan"
    # 历史识别字段（可选）
    agent_type: Literal["planning"] = "planning"
    department: str = Field(default="")
    goal: str = Field(..., min_length=1)
    success_hint: str = Field(default="")
    success_when: Literal["gate_decided", "none"] = "gate_decided"
    tone: PlanningTone
    allowed_tools: list[str] = Field(..., min_length=1)
    system_extra: str = Field(default="")
    output_format: str = Field(default="")
    # Story2 / flows 机读协作（可选）
    flow_ids: list[str] = Field(default_factory=list)
    consumes_from: list[str] = Field(default_factory=list)

    @field_validator("allowed_tools", "flow_ids", "consumes_from")
    @classmethod
    def _uniq_str_list(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        for name in v:
            name = str(name).strip()
            if name and name not in out:
                out.append(name)
        return out

    @field_validator("allowed_tools")
    @classmethod
    def _tools_nonempty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("allowed_tools 不能为空")
        return v
