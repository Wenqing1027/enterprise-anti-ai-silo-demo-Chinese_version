"""数据模型 · finance（由标准字段定义表生成）。"""

from __future__ import annotations

from pydantic import Field

from shared.models.base import QingshuModel
from shared.models.enums import MatchStatus

class Finance(QingshuModel):
    """财经 · Finance。字段来自《标准字段定义表》。"""

    expense_id: str | None = Field(
        default=None,
        description="报销单号。报销单",
        json_schema_extra={"example": "EXP-202607-118"},
    )
    invoice_no: str | None = Field(
        default=None,
        description="发票号。发票号",
        json_schema_extra={"example": "INV-8891200"},
    )
    po_no: str | None = Field(
        default=None,
        description="采购订单号。PO号",
        json_schema_extra={"example": "PO-55201"},
    )
    receipt_amt: float | None = Field(
        default=None,
        description="回单金额。回单",
        json_schema_extra={"example": "1280.00"},
    )
    invoice_amt: float | None = Field(
        default=None,
        description="发票金额。发票",
        json_schema_extra={"example": "1280.00"},
    )
    po_amt: float | None = Field(
        default=None,
        description="PO金额。采购订单金额",
        json_schema_extra={"example": "1300.00"},
    )
    match_status: MatchStatus | None = Field(
        default=None,
        description="三单匹配状态。match|mismatch",
        json_schema_extra={"example": "mismatch"},
    )
    diff_amt: float | None = Field(
        default=None,
        description="差异金额。差异",
        json_schema_extra={"example": "20.00"},
    )
    diff_reason: str | None = Field(
        default=None,
        description="差异原因。差异归因",
        json_schema_extra={"example": "税额不符"},
    )
    revenue_forecast: float | None = Field(
        default=None,
        description="收入预测。月收入预测",
        json_schema_extra={"example": "1.2e8"},
    )
    pickup_forecast_units: int | None = Field(
        default=None,
        description="提货预测台数。提货预测",
        json_schema_extra={"example": "52000"},
    )
    rebate_cashout_forecast: float | None = Field(
        default=None,
        description="返利兑付预测。返利现金流出",
        json_schema_extra={"example": "8.5e6"},
    )
    opex_forecast: float | None = Field(
        default=None,
        description="费用预测。OPEX预测",
        json_schema_extra={"example": "2.1e7"},
    )
    net_cash_forecast: float | None = Field(
        default=None,
        description="净现金流预测。净现金流",
        json_schema_extra={"example": "1.5e7"},
    )
    forecast_confidence_low: float | None = Field(
        default=None,
        description="预测下限。置信区间低",
        json_schema_extra={"example": "1.1e7"},
    )
    forecast_confidence_high: float | None = Field(
        default=None,
        description="预测上限。置信区间高",
        json_schema_extra={"example": "1.9e7"},
    )
