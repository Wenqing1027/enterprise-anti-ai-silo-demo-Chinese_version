"""数据模型 · meta（由标准字段定义表生成）。"""

from __future__ import annotations

from datetime import date, datetime

from typing import Any

from pydantic import Field

from shared.models.base import QingshuModel
from shared.models.enums import PeriodType, TrafficLight

class ReportMeta(QingshuModel):
    """元数据 · ReportMeta。字段来自《标准字段定义表》。"""

    report_id: str | None = Field(
        default=None,
        description="报表ID。单次报表实例唯一标识",
        json_schema_extra={"example": "CH-RPT-2026-07-EAST"},
    )
    report_type: str | None = Field(
        default=None,
        description="报表类型。报表类型编码",
        json_schema_extra={"example": "channel_analysis"},
    )
    period: str | None = Field(
        default=None,
        description="统计周期。月/周/日/自定义区间",
        json_schema_extra={"example": "2026-07"},
    )
    period_type: PeriodType | None = Field(
        default=None,
        description="周期类型。day|week|month|quarter|custom",
        json_schema_extra={"example": "month"},
    )
    period_start: date | None = Field(
        default=None,
        description="周期开始。统计起始日",
        json_schema_extra={"example": "2026-07-01"},
    )
    period_end: date | None = Field(
        default=None,
        description="周期结束。统计结束日",
        json_schema_extra={"example": "2026-07-31"},
    )
    generated_at: datetime | None = Field(
        default=None,
        description="生成时间。报表生成时间戳",
        json_schema_extra={"example": "2026-08-01T10:00:00+08:00"},
    )
    data_as_of: datetime | None = Field(
        default=None,
        description="数据截止时点。取数截止时点",
        json_schema_extra={"example": "2026-07-31T23:59:59+08:00"},
    )
    run_id: str | None = Field(
        default=None,
        description="运行ID。Agent/流水线运行ID",
        json_schema_extra={"example": "run_abc123"},
    )
    producer_skill: str | None = Field(
        default=None,
        description="产出Skill。写入共享层的生产者",
        json_schema_extra={"example": "channel_analysis"},
    )
    traffic_light: TrafficLight | None = Field(
        default=None,
        description="红黄绿灯。red|yellow|green",
        json_schema_extra={"example": "yellow"},
    )
    narrative_summary: str | None = Field(
        default=None,
        description="NLG摘要。自然语言摘要",
        json_schema_extra={"example": "东区提货达成83%，颜色缺货为第一异常因"},
    )
    action_suggestions: Any | None = Field(
        default=None,
        description="行动建议列表。结构化建议数组",
    )
