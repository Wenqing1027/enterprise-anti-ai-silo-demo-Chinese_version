"""Extraction Skill 契约（与 ReAct SkillConfig 分离）。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


PayloadSchemaId = Literal["ticket_draft_v1", "voc_entities_v1"]


class ExtractionTone(BaseModel):
    label: str = Field(..., min_length=1)
    style: str = Field(..., min_length=1)
    forbid: str = Field(default="")


class ExtractionSecurity(BaseModel):
    prompt_forbid_extra: str = Field(default="")
    redact_pii: bool = True


class ExtractionSkillConfig(BaseModel):
    skill_id: str = Field(..., min_length=1)
    control_loop: Literal["extract"] = Field(
        default="extract",
        description="平台控制环归属（Extract Skill 固定 extract）",
    )
    department: str = Field(default="")
    goal: str = Field(..., min_length=1)
    success_hint: str = Field(default="")
    payload_schema: PayloadSchemaId
    write_ai_output: bool = True
    consumer_allow: list[str] = Field(default_factory=list)
    tone: ExtractionTone
    extract_rules: str = Field(default="", description="覆盖默认 E_extract_rules")
    dictionary_extra: str = Field(default="", description="追加到标签字典段")
    security: ExtractionSecurity = Field(default_factory=ExtractionSecurity)
    max_schema_retries: int = Field(default=1, ge=0, le=2)
    max_input_chars: int = Field(default=4000, ge=200, le=8000)

    @field_validator("consumer_allow")
    @classmethod
    def _uniq_consumers(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        for name in v:
            name = str(name).strip()
            if name and name not in out:
                out.append(name)
        return out


EXTRACTION_PROMPT_SECTION_ORDER: tuple[str, ...] = (
    "A_base",
    "B_schema",
    "C_goal",
    "D_dictionary",
    "E_extract_rules",
    "F_output",
    "G_security",
)
