"""数据模型 · product（由标准字段定义表生成）。"""

from __future__ import annotations

from datetime import date

from pydantic import Field

from shared.models.base import QingshuModel
from shared.models.enums import HotSlowFlag

class SKU(QingshuModel):
    """商品SKU · SKU。字段来自《标准字段定义表》。"""

    sku_id: str | None = Field(
        default=None,
        description="SKU ID。SKU唯一ID",
        json_schema_extra={"example": "SKU-E60-BK"},
    )
    sku_name: str | None = Field(
        default=None,
        description="SKU名称。SKU显示名",
        json_schema_extra={"example": "E60 哑光黑"},
    )
    asp_cny: float | None = Field(
        default=None,
        description="平均售价ASP。台均价",
        json_schema_extra={"example": "3299"},
    )
    hot_slow_flag: HotSlowFlag | None = Field(
        default=None,
        description="爆滞标记。hot|normal|slow",
        json_schema_extra={"example": "hot"},
    )
    substitute_sku_id: str | None = Field(
        default=None,
        description="替代SKU。缺货替代映射",
        json_schema_extra={"example": "SKU-E60-GY"},
    )

class Competitor(QingshuModel):
    """商品SKU · Competitor。字段来自《标准字段定义表》。"""

    competitor_brand: str | None = Field(
        default=None,
        description="竞品品牌。竞品品牌名",
        json_schema_extra={"example": "雅迪"},
    )
    competitor_model: str | None = Field(
        default=None,
        description="竞品车型。竞品车型名",
        json_schema_extra={"example": "冠能XX"},
    )
    competitor_price_cny: float | None = Field(
        default=None,
        description="竞品价格。竞品挂牌/活动价",
        json_schema_extra={"example": "3699"},
    )
    competitor_share: float | None = Field(
        default=None,
        description="竞品区域份额。区域市占",
        json_schema_extra={"example": "28.0"},
    )
    competitor_share_pp_change: float | None = Field(
        default=None,
        description="份额变化百分点。份额环比变化",
        json_schema_extra={"example": "-1.2"},
    )
    promo_type: str | None = Field(
        default=None,
        description="促销类型。活动类型",
        json_schema_extra={"example": "以旧换新"},
    )
    promo_region: str | None = Field(
        default=None,
        description="促销区域。活动区域",
        json_schema_extra={"example": "苏皖"},
    )
    promo_window: str | None = Field(
        default=None,
        description="促销窗口。活动时间窗",
        json_schema_extra={"example": "2026-07-01~07-31"},
    )
    price_cut_amt: float | None = Field(
        default=None,
        description="降价金额。降价幅度",
        json_schema_extra={"example": "300"},
    )
    sentiment_score: float | None = Field(
        default=None,
        description="口碑分。竞品口碑",
        json_schema_extra={"example": "0.62"},
    )
    launch_date: date | None = Field(
        default=None,
        description="上市日期。竞品上市日",
        json_schema_extra={"example": "2026-06-18"},
    )
