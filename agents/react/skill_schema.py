"""skill.yaml 格式定义（唯一契约）。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class SkillTone(BaseModel):
    label: str = Field(..., min_length=1, description="风格标签，如「稳妥确认型」")
    style: str = Field(..., min_length=1, description="语气要点")
    forbid: str = Field(default="", description="禁用项")


class SkillSecurity(BaseModel):
    """模块四：Skill 级安全槽。"""

    kb_domains_allow: list[str] = Field(
        default_factory=list,
        description="非空时限制 search_kb.domain",
    )
    max_tool_calls_per_step: int = Field(default=6, ge=1, le=20)
    redact_pii_in_observation: bool = True
    block_on_outreach: bool = False
    prompt_forbid_extra: str = Field(
        default="",
        description="追加进 Prompt F_security 的硬禁表述",
    )

    @field_validator("kb_domains_allow")
    @classmethod
    def _kb_domains(cls, v: list[str]) -> list[str]:
        allowed = {"repair", "policy", "hr", "product", "channel"}
        out: list[str] = []
        for d in v:
            key = str(d).strip().lower()
            if not key:
                continue
            if key not in allowed:
                raise ValueError(f"kb domain 非法: {key}; 允许 {sorted(allowed)}")
            if key not in out:
                out.append(key)
        return out


class SkillConfig(BaseModel):
    """skills/<id>/skill.yaml 的规范形状。"""

    skill_id: str = Field(..., min_length=1)
    control_loop: Literal["act"] = Field(
        default="act",
        description="平台控制环归属（Act Skill 固定 act）",
    )
    department: str = Field(default="", description="主责部门叙事")
    goal: str = Field(..., min_length=1, description="一句话任务目标")
    success_hint: str = Field(default="", description="成功标准说明（给人看）")
    success_when: str = Field(
        default="none",
        description="机器可判成功条件：wrote_ai_output|master_lookup|channel_lookup|none",
    )
    max_steps: int = Field(default=8, ge=1, le=32)
    tone: SkillTone
    allowed_tools: list[str] = Field(..., min_length=1)
    system_extra: str = Field(default="", description="并入 Prompt [C] 任务目标之后")
    output_format: str = Field(default="", description="并入 Prompt [E] 终答格式")
    security: SkillSecurity = Field(default_factory=SkillSecurity)

    @field_validator("allowed_tools")
    @classmethod
    def _uniq_tools(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        for name in v:
            name = str(name).strip()
            if name and name not in out:
                out.append(name)
        if not out:
            raise ValueError("allowed_tools 不能为空")
        return out

    @field_validator("success_when")
    @classmethod
    def _success_when(cls, v: str) -> str:
        allowed = {
            "none",
            "wrote_ai_output",
            "master_lookup",
            "channel_lookup",
        }
        key = (v or "none").strip()
        if key not in allowed:
            raise ValueError(f"success_when 必须是 {sorted(allowed)} 之一")
        return key


# 与模块三/四文档一致的拼段顺序（不可在调用处打乱）
PROMPT_SECTION_ORDER: tuple[str, ...] = (
    "A_base",
    "B_tone",
    "C_goal",
    "C2_system_extra",
    "D_tools",
    "E_output",
    "F_security",
)


def skill_to_prompt_dict(cfg: SkillConfig) -> dict[str, Any]:
    """供调试用的字典视图。"""
    return cfg.model_dump()
