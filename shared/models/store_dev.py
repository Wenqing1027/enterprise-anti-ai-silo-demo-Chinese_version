"""数据模型 · store_dev（由标准字段定义表生成）。"""

from __future__ import annotations

from datetime import date

from pydantic import Field

from shared.models.base import QingshuModel
from shared.models.enums import AdmissionSuggest, RiskLevel, SelfCoverageFlag, StoreGrade

class StoreDev(QingshuModel):
    """渠道开发 · StoreDev。字段来自《标准字段定义表》。"""

    blank_l1_plan_cnt: int | None = Field(
        default=None,
        description="空白一网计划数。计划开发空白一网",
        json_schema_extra={"example": "18"},
    )
    blank_l1_opened_cnt: int | None = Field(
        default=None,
        description="空白一网已开数。已开空白一网",
        json_schema_extra={"example": "11"},
    )
    blank_l1_achieve_rate: float | None = Field(
        default=None,
        description="空白一网达成率。已开/计划",
        json_schema_extra={"example": "61.1"},
    )
    store_dev_plan_cnt: int | None = Field(
        default=None,
        description="门店开发计划数。年度开发计划",
        json_schema_extra={"example": "120"},
    )
    store_dev_done_cnt: int | None = Field(
        default=None,
        description="门店开发完成数。累计完成",
        json_schema_extra={"example": "74"},
    )
    store_dev_rate: float | None = Field(
        default=None,
        description="门店开发完成率。完成/计划",
        json_schema_extra={"example": "61.7"},
    )
    market_capacity_annual: int | None = Field(
        default=None,
        description="县域年市场容量。两轮电动年容量",
        json_schema_extra={"example": "42000"},
    )
    self_coverage_flag: SelfCoverageFlag | None = Field(
        default=None,
        description="本品覆盖标记。yes|weak|blank",
        json_schema_extra={"example": "blank"},
    )
    open_roi_months: float | None = Field(
        default=None,
        description="开店回收月数。投资回收预测",
        json_schema_extra={"example": "14"},
    )
    support_quota_total_wan: float | None = Field(
        default=None,
        description="支持额度总额。开店支持总额度",
        json_schema_extra={"example": "15"},
    )
    support_quota_applied_wan: float | None = Field(
        default=None,
        description="已申请额度。已申请",
        json_schema_extra={"example": "8"},
    )
    support_quota_remain_wan: float | None = Field(
        default=None,
        description="剩余额度。剩余",
        json_schema_extra={"example": "7"},
    )
    first_order_qty: int | None = Field(
        default=None,
        description="首批订单量。新商首批提货",
        json_schema_extra={"example": "80"},
    )
    m1_m3_order_qty: int | None = Field(
        default=None,
        description="1-3月订单量。新商前三月提货",
        json_schema_extra={"example": "210"},
    )
    gantt_owner: str | None = Field(
        default=None,
        description="开店负责人。开店甘特负责人",
        json_schema_extra={"example": "张三"},
    )
    gantt_start: date | None = Field(
        default=None,
        description="开店开始日。甘特开始",
        json_schema_extra={"example": "2026-07-01"},
    )
    gantt_end: date | None = Field(
        default=None,
        description="开店结束日。甘特结束",
        json_schema_extra={"example": "2026-09-15"},
    )
    fitout_suggest_grade: StoreGrade | None = Field(
        default=None,
        description="装修建议等级。装修定级建议",
        json_schema_extra={"example": "B"},
    )

class Risk(QingshuModel):
    """渠道开发 · Risk。字段来自《标准字段定义表》。"""

    credit_code: str | None = Field(
        default=None,
        description="统一社会信用代码。工商代码",
        json_schema_extra={"example": "9132XXXXXXXX"},
    )
    reg_capital_wan: float | None = Field(
        default=None,
        description="注册资本。注册资本",
        json_schema_extra={"example": "500"},
    )
    lawsuit_cnt_3y: int | None = Field(
        default=None,
        description="近3年诉讼数。司法风险",
        json_schema_extra={"example": "2"},
    )
    dishonest_flag: bool | None = Field(
        default=None,
        description="是否失信。失信被执行",
        json_schema_extra={"example": "false"},
    )
    negative_news_cnt_90d: int | None = Field(
        default=None,
        description="近90天负面舆情数。舆情风险",
        json_schema_extra={"example": "1"},
    )
    risk_level: RiskLevel | None = Field(
        default=None,
        description="风险等级。low|medium|high",
        json_schema_extra={"example": "medium"},
    )
    risk_score: float | None = Field(
        default=None,
        description="风险评分。综合风险分",
        json_schema_extra={"example": "62"},
    )
    admission_suggest: AdmissionSuggest | None = Field(
        default=None,
        description="准入建议。pass|supplement|reject",
        json_schema_extra={"example": "supplement"},
    )
