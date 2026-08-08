"""数据模型 · inspection（由标准字段定义表生成）。"""

from __future__ import annotations

from datetime import date, datetime

from typing import Any

from pydantic import Field

from shared.models.base import QingshuModel
from shared.models.enums import PassFail

class Inspection(QingshuModel):
    """巡检合规 · Inspection。字段来自《标准字段定义表》。"""

    inspect_id: str | None = Field(
        default=None,
        description="巡检ID。巡检任务ID",
        json_schema_extra={"example": "INS-20260728-014"},
    )
    inspect_time: datetime | None = Field(
        default=None,
        description="巡检时间。巡检时间",
        json_schema_extra={"example": "2026-07-28T08:30:00+08:00"},
    )
    check_item: str | None = Field(
        default=None,
        description="查检项。查检项名称",
        json_schema_extra={"example": "门头VI完整性"},
    )
    ai_confidence: float | None = Field(
        default=None,
        description="AI置信度。视觉识别置信度",
        json_schema_extra={"example": "0.91"},
    )
    pass_fail: PassFail | None = Field(
        default=None,
        description="通过/驳回。pass|fail",
        json_schema_extra={"example": "fail"},
    )
    photo_url: str | None = Field(
        default=None,
        description="照片URL。证据图",
        json_schema_extra={"example": "https://.../store.jpg"},
    )
    morning_photo_url: str | None = Field(
        default=None,
        description="早全景照URL。早晚差分-早",
        json_schema_extra={"example": "https://.../am.jpg"},
    )
    evening_photo_url: str | None = Field(
        default=None,
        description="晚全景照URL。早晚差分-晚",
        json_schema_extra={"example": "https://.../pm.jpg"},
    )
    competitor_logo_detected: Any | None = Field(
        default=None,
        description="检出竞品Logo。竞品标识检测",
    )
    suspect_type: str | None = Field(
        default=None,
        description="疑点类型。违规疑点类型",
        json_schema_extra={"example": "非专卖堆货"},
    )
    vi_score: float | None = Field(
        default=None,
        description="VI一致性分。VI评分",
        json_schema_extra={"example": "78"},
    )
    rectify_ticket_id: str | None = Field(
        default=None,
        description="整改工单号。整改单",
        json_schema_extra={"example": "RC-8891"},
    )
    due_date: date | None = Field(
        default=None,
        description="整改截止日。整改期限",
        json_schema_extra={"example": "2026-08-05"},
    )

class Brand(QingshuModel):
    """巡检合规 · Brand。字段来自《标准字段定义表》。"""

    mention_cnt_24h: int | None = Field(
        default=None,
        description="24h品牌提及量。舆情提及",
        json_schema_extra={"example": "1260"},
    )
    reputation_score: float | None = Field(
        default=None,
        description="声誉分。品牌声誉",
        json_schema_extra={"example": "71"},
    )
    hotspot_term: str | None = Field(
        default=None,
        description="热点词。舆情热点",
        json_schema_extra={"example": "续航虚标"},
    )
    growth_velocity: float | None = Field(
        default=None,
        description="声量增速。突增速度",
        json_schema_extra={"example": "3.2"},
    )
    mi_consistency_score: float | None = Field(
        default=None,
        description="MI言行一致分。理念-言行一致",
        json_schema_extra={"example": "66"},
    )
    bvp_memorability: float | None = Field(
        default=None,
        description="BVP记忆度。BVP测试",
        json_schema_extra={"example": "0.42"},
    )
    bvp_understanding: float | None = Field(
        default=None,
        description="BVP理解度。BVP测试",
        json_schema_extra={"example": "0.55"},
    )
    purchase_intent: float | None = Field(
        default=None,
        description="购买意愿。BVP/调研",
        json_schema_extra={"example": "0.48"},
    )
    energy_kwh_per_vehicle: float | None = Field(
        default=None,
        description="单车能耗。制造能耗",
        json_schema_extra={"example": "128"},
    )
    co2e_t: float | None = Field(
        default=None,
        description="碳排放当量。排放",
        json_schema_extra={"example": " sequester"},
    )
    scrap_battery_recycle_rate: float | None = Field(
        default=None,
        description="废旧电池回收率。回收率",
        json_schema_extra={"example": "91.0"},
    )
