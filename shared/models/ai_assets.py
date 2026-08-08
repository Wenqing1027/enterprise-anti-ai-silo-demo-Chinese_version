"""数据模型 · ai_assets（由标准字段定义表生成，并按 BLUEPRINT L7 补齐）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from shared.models.base import QingshuModel
from shared.models.enums import StepStatus, TagDomain


class AIOutput(QingshuModel):
    """共享AI资产 · AIOutput。

    标准字段 + BLUEPRINT：`id, producer_skill, consumer_allow, payload, run_id, ts`。
    """

    ai_output_id: str | None = Field(
        default=None,
        description="AI产出ID。共享产出唯一ID",
        json_schema_extra={"example": "AIO-10001"},
    )
    producer_skill: str | None = Field(
        default=None,
        description="生产者Skill。产出方skill_id",
        json_schema_extra={"example": "fill_ticket"},
    )
    consumer_allow: list[str] | None = Field(
        default=None,
        description="允许消费方。可订阅skill列表",
    )
    payload: dict[str, Any] | list[Any] | None = Field(
        default=None,
        description="产出载荷。结构化产出内容",
    )
    payload_schema: str | None = Field(
        default=None,
        description="载荷Schema。载荷结构版本",
        json_schema_extra={"example": "ticket_draft_v1"},
    )
    run_id: str | None = Field(
        default=None,
        description="运行ID。产出所属 Agent run",
        json_schema_extra={"example": "run_abc123"},
    )
    ts: datetime | None = Field(
        default=None,
        description="产出时间戳",
        json_schema_extra={"example": "2026-08-01T12:00:00+08:00"},
    )


class TagVocabulary(QingshuModel):
    """共享AI资产 · TagVocabulary。共享语义标签字典。"""

    tag_id: str | None = Field(
        default=None,
        description="标签ID。标准标签唯一ID（共享语义）",
        json_schema_extra={"example": "TAG-续航短"},
    )
    tag_name: str | None = Field(
        default=None,
        description="标签名称。标签显示名",
        json_schema_extra={"example": "续航短"},
    )
    tag_domain: TagDomain | None = Field(
        default=None,
        description="标签域。product|service|app|channel|risk",
        json_schema_extra={"example": "product"},
    )
    tag_parent_id: str | None = Field(
        default=None,
        description="父标签ID。标签树",
        json_schema_extra={"example": "TAG-整车体验"},
    )
    tag_vocab_version: str | None = Field(
        default=None,
        description="标签字典版本。共享语义版本",
        json_schema_extra={"example": "voc-tags-2026.07"},
    )


class CapabilityCatalog(QingshuModel):
    """共享AI资产 · CapabilityCatalog。能力目录。"""

    skill_id: str | None = Field(
        default=None,
        description="Skill ID。能力目录主键",
        json_schema_extra={"example": "repair_kb"},
    )
    skill_desc: str | None = Field(
        default=None,
        description="Skill描述。能力说明",
        json_schema_extra={"example": "维修知识库问答"},
    )
    input_schema: dict[str, Any] | None = Field(
        default=None,
        description="输入Schema。输入约定",
    )
    output_schema: dict[str, Any] | None = Field(
        default=None,
        description="输出Schema。输出约定",
    )
    allowed_tools: list[str] | None = Field(
        default=None,
        description="可用Tools。可调用工具列表",
    )


class RunLog(QingshuModel):
    """共享AI资产 · RunLog。协作层步骤日志。"""

    run_id: str | None = Field(
        default=None,
        description="运行ID",
        json_schema_extra={"example": "run_abc123"},
    )
    step_name: str | None = Field(
        default=None,
        description="步骤名。控制环步骤",
        json_schema_extra={"example": "retrieve"},
    )
    step_status: StepStatus | None = Field(
        default=None,
        description="步骤状态。ok|error|skipped",
        json_schema_extra={"example": "ok"},
    )
    step_ts: datetime | None = Field(
        default=None,
        description="步骤时间。步骤时间戳",
        json_schema_extra={"example": "2026-08-01T12:00:00+08:00"},
    )
    detail: dict[str, Any] | None = Field(
        default=None,
        description="步骤详情（可选）",
    )
