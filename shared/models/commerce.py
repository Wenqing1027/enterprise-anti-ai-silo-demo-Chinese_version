"""数据模型 · commerce（由标准字段定义表生成）。"""

from __future__ import annotations

from datetime import date

from pydantic import Field

from shared.models.base import QingshuModel
from shared.models.enums import AuditResult, OrderStatus, PayStatus, ShortageRootCause

class Order(QingshuModel):
    """订单库存政策 · Order。字段来自《标准字段定义表》+ 关联键。"""

    order_id: str | None = Field(
        default=None,
        description="订单号。订单唯一号",
        json_schema_extra={"example": "SO-77821"},
    )
    dealer_id: str | None = Field(
        default=None,
        description="经销商ID。关联 Dealer",
        json_schema_extra={"example": "DLR-3201"},
    )
    store_id: str | None = Field(
        default=None,
        description="门店ID。关联 Store",
        json_schema_extra={"example": "ST-8891"},
    )
    sku_id: str | None = Field(
        default=None,
        description="SKU ID。关联 SKU",
        json_schema_extra={"example": "SKU-E60-BK"},
    )
    customer_id: str | None = Field(
        default=None,
        description="客户ID。关联 Customer（若 C 端订单）",
        json_schema_extra={"example": "CUS-10086"},
    )
    order_qty: int | None = Field(
        default=None,
        description="订单数量。下单台数",
        json_schema_extra={"example": "30"},
    )
    order_status: OrderStatus | None = Field(
        default=None,
        description="订单状态。草稿/待审/通过/驳回/发货/完成",
        json_schema_extra={"example": "pending_audit"},
    )
    audit_result: AuditResult | None = Field(
        default=None,
        description="审单结果。通过|缺货驳回|建议替代",
        json_schema_extra={"example": "suggest_substitute"},
    )
    policy_version: str | None = Field(
        default=None,
        description="政策版本。下单时适用政策",
        json_schema_extra={"example": "2026Q3-提货返利-V3"},
    )

class Inventory(QingshuModel):
    """订单库存政策 · Inventory。字段来自《标准字段定义表》+ 关联键。"""

    sku_id: str | None = Field(
        default=None,
        description="SKU ID。关联 SKU",
        json_schema_extra={"example": "SKU-E60-BK"},
    )
    store_id: str | None = Field(
        default=None,
        description="门店ID。门店库存维度（可选）",
        json_schema_extra={"example": "ST-8891"},
    )
    dealer_id: str | None = Field(
        default=None,
        description="经销商ID。库存归属（可选）",
        json_schema_extra={"example": "DLR-3201"},
    )
    wms_stock_qty: int | None = Field(
        default=None,
        description="WMS库存。仓内库存",
        json_schema_extra={"example": "120"},
    )
    wms_in_transit_qty: int | None = Field(
        default=None,
        description="WMS在途。在途数量",
        json_schema_extra={"example": "45"},
    )
    store_stock_qty: int | None = Field(
        default=None,
        description="门店库存。门店现货",
        json_schema_extra={"example": "8"},
    )
    stock_days_cover: float | None = Field(
        default=None,
        description="库存可售天数。库存覆盖天数",
        json_schema_extra={"example": "1.2"},
    )
    stock_age_days: int | None = Field(
        default=None,
        description="库龄天数。滞销库龄",
        json_schema_extra={"example": "51"},
    )
    inventory_turn_days: float | None = Field(
        default=None,
        description="库存周转天数。周转天数",
        json_schema_extra={"example": "28"},
    )
    shortage_days: int | None = Field(
        default=None,
        description="断货天数。持续缺货天数",
        json_schema_extra={"example": "11"},
    )
    demand_daily_est: float | None = Field(
        default=None,
        description="日均需求估计。需求估计",
        json_schema_extra={"example": "18"},
    )
    lost_units_est: int | None = Field(
        default=None,
        description="估损台数。断货损失台数",
        json_schema_extra={"example": "198"},
    )
    lost_gmv_est: float | None = Field(
        default=None,
        description="估损GMV。断货损失销售额",
        json_schema_extra={"example": "653202"},
    )
    lost_margin_est: float | None = Field(
        default=None,
        description="估损毛利。断货损失毛利",
        json_schema_extra={"example": "117576"},
    )
    shortage_root_cause: ShortageRootCause | None = Field(
        default=None,
        description="断货根因。排产|物流|颜色计划|供应",
        json_schema_extra={"example": "color_plan"},
    )
    replenish_qty_suggest: int | None = Field(
        default=None,
        description="建议补货量。建议补货",
        json_schema_extra={"example": "200"},
    )
    eta_date: date | None = Field(
        default=None,
        description="预计到货日。补货ETA",
        json_schema_extra={"example": "2026-08-05"},
    )

class Policy(QingshuModel):
    """订单库存政策 · Policy。字段来自《标准字段定义表》。"""

    policy_version: str | None = Field(
        default=None,
        description="政策版本。销售政策版本",
        json_schema_extra={"example": "2026Q3-提货返利-V3"},
    )
    current_rebate_tier: str | None = Field(
        default=None,
        description="当前返利档位。当前档位名",
        json_schema_extra={"example": "银牌档"},
    )
    current_pickup_qty_mtd: int | None = Field(
        default=None,
        description="本月已提货。当月累计提货",
        json_schema_extra={"example": "612"},
    )
    qty_to_next_tier: int | None = Field(
        default=None,
        description="距下一档台数。冲档缺口",
        json_schema_extra={"example": "188"},
    )
    next_tier_name: str | None = Field(
        default=None,
        description="下一档位名。目标档位",
        json_schema_extra={"example": "金牌档"},
    )
    next_tier_rebate_amt: float | None = Field(
        default=None,
        description="达下一档预计返利。冲档返利增量",
        json_schema_extra={"example": "28000"},
    )
    rebate_rate: float | None = Field(
        default=None,
        description="返利点数。返利比例",
        json_schema_extra={"example": "3.5"},
    )
    color_bonus_amt: float | None = Field(
        default=None,
        description="颜色齐全奖励。颜色点位奖励",
        json_schema_extra={"example": "2000"},
    )
    clawback_amt: float | None = Field(
        default=None,
        description="扣回金额。违规/未达扣回",
        json_schema_extra={"example": "500"},
    )
    payable_amt: float | None = Field(
        default=None,
        description="应结金额。应付返利",
        json_schema_extra={"example": "29500"},
    )
    settlement_id: str | None = Field(
        default=None,
        description="结算单号。结算单ID",
        json_schema_extra={"example": "STL-2026Q3-3201"},
    )
    pay_status: PayStatus | None = Field(
        default=None,
        description="支付状态。unpaid|paid|exception",
        json_schema_extra={"example": "unpaid"},
    )

class ColorPlan(QingshuModel):
    """订单库存政策 · ColorPlan。字段来自《标准字段定义表》。"""

    color_plan_week: str | None = Field(
        default=None,
        description="颜色排产周。排产周次",
        json_schema_extra={"example": "2026-W31"},
    )
    color_plan_qty: int | None = Field(
        default=None,
        description="颜色计划产量。该颜色计划产量",
        json_schema_extra={"example": "120"},
    )
