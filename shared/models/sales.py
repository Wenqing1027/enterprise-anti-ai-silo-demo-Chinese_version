"""数据模型 · sales（由标准字段定义表生成）。"""

from __future__ import annotations

from pydantic import Field

from shared.models.base import QingshuModel

class SalesMetric(QingshuModel):
    """销售目标 · SalesMetric。字段来自《标准字段定义表》。"""

    sales_qty: int | None = Field(
        default=None,
        description="提货/销量台数。提货口径销量",
        json_schema_extra={"example": "12480"},
    )
    sales_target_qty: int | None = Field(
        default=None,
        description="销量目标台数。考核销量目标",
        json_schema_extra={"example": "15000"},
    )
    sales_achieve_rate: float | None = Field(
        default=None,
        description="销量达成率。销量/目标",
        json_schema_extra={"example": "83.2"},
    )
    contract_qty: int | None = Field(
        default=None,
        description="签约量。签约台数",
        json_schema_extra={"example": "11200"},
    )
    contract_target_qty: int | None = Field(
        default=None,
        description="签约目标。签约目标",
        json_schema_extra={"example": "13000"},
    )
    contract_achieve_rate: float | None = Field(
        default=None,
        description="签约达成率。签约/目标",
        json_schema_extra={"example": "86.2"},
    )
    yoy_sales_qty: int | None = Field(
        default=None,
        description="去年同期销量。同比基期销量",
        json_schema_extra={"example": "10900"},
    )
    yoy_rate: float | None = Field(
        default=None,
        description="同比增长率。同比",
        json_schema_extra={"example": "14.5"},
    )
    mom_sales_qty: int | None = Field(
        default=None,
        description="上月销量。环比基期",
        json_schema_extra={"example": "13100"},
    )
    mom_rate: float | None = Field(
        default=None,
        description="环比增长率。环比",
        json_schema_extra={"example": "-4.7"},
    )
    rank_warzone: int | None = Field(
        default=None,
        description="大战区排名。大战区排名",
        json_schema_extra={"example": "2"},
    )
    rank_subzone: int | None = Field(
        default=None,
        description="小战区排名。小战区排名",
        json_schema_extra={"example": "5"},
    )
    rank_dealer: int | None = Field(
        default=None,
        description="一代排名。一代排名",
        json_schema_extra={"example": "18"},
    )
    full_achieve_outlet_cnt: int | None = Field(
        default=None,
        description="100%达成网点数。满分网点数",
        json_schema_extra={"example": "86"},
    )
    full_achieve_outlet_ratio: float | None = Field(
        default=None,
        description="100%达成网点占比。满分网点占比",
        json_schema_extra={"example": "41.3"},
    )
    abnormal_outlet_cnt: int | None = Field(
        default=None,
        description="异常网点数。异常网点数量",
        json_schema_extra={"example": "23"},
    )
    abnormal_outlet_ratio: float | None = Field(
        default=None,
        description="异常网点占比。异常占比",
        json_schema_extra={"example": "11.1"},
    )
    abnormal_reason: str | None = Field(
        default=None,
        description="异常原因。异常归因",
        json_schema_extra={"example": "颜色缺货"},
    )
    abnormal_reason_cnt: int | None = Field(
        default=None,
        description="异常原因次数。该原因出现次数",
        json_schema_extra={"example": "9"},
    )
    core_market_gap_to_top3: int | None = Field(
        default=None,
        description="核心市场前三差距。与区域第一差距",
        json_schema_extra={"example": "1260"},
    )
    online_sales_qty: int | None = Field(
        default=None,
        description="线上销量。电商/直播销量",
        json_schema_extra={"example": "860"},
    )

class Health(QingshuModel):
    """销售目标 · Health。字段来自《标准字段定义表》。"""

    health_index: float | None = Field(
        default=None,
        description="经营健康指数。一代综合健康分",
        json_schema_extra={"example": "72"},
    )
    sales_score: float | None = Field(
        default=None,
        description="销量分项分。健康指数分项",
        json_schema_extra={"example": "75"},
    )
    retail_score: float | None = Field(
        default=None,
        description="零售分项分。健康指数分项",
        json_schema_extra={"example": "68"},
    )
    compliance_score: float | None = Field(
        default=None,
        description="合规分项分。健康指数分项",
        json_schema_extra={"example": "80"},
    )
    complaint_score: float | None = Field(
        default=None,
        description="客诉分项分。健康指数分项",
        json_schema_extra={"example": "70"},
    )
    inventory_turn_score: float | None = Field(
        default=None,
        description="库存周转分项分。健康指数分项",
        json_schema_extra={"example": "65"},
    )
