"""数据模型 · channel（由标准字段定义表生成）。"""

from __future__ import annotations

from datetime import date

from pydantic import Field

from shared.models.base import QingshuModel
from shared.models.enums import StoreGrade, StoreType

class Dealer(QingshuModel):
    """渠道主数据 · Dealer。字段来自《标准字段定义表》。"""

    dealer_id: str | None = Field(
        default=None,
        description="一代/经销商ID。经销商唯一ID",
        json_schema_extra={"example": "DLR-3201"},
    )
    dealer_name: str | None = Field(
        default=None,
        description="经销商名称。经销商名",
        json_schema_extra={"example": "青枢南京江宁一网"},
    )
    legal_person: str | None = Field(
        default=None,
        description="法人。工商法人",
        json_schema_extra={"example": "王某某"},
    )
    open_account_date: date | None = Field(
        default=None,
        description="开户时间。经销商开户日",
        json_schema_extra={"example": "2024-03-12"},
    )
    developer_name: str | None = Field(
        default=None,
        description="开发人员。渠道开发负责人",
        json_schema_extra={"example": "李开发"},
    )

class Store(QingshuModel):
    """渠道主数据 · Store。字段来自《标准字段定义表》。"""

    store_id: str | None = Field(
        default=None,
        description="门店ID。门店唯一ID",
        json_schema_extra={"example": "ST-8891"},
    )
    store_name: str | None = Field(
        default=None,
        description="门店名称。门店名",
        json_schema_extra={"example": "青枢南京江宁专卖店"},
    )
    store_address: str | None = Field(
        default=None,
        description="门店地址。详细地址",
        json_schema_extra={"example": "江宁区东山街道XX路88号"},
    )
    store_type: StoreType | None = Field(
        default=None,
        description="门店类型。exclusive|mixed|non_exclusive",
        json_schema_extra={"example": "exclusive"},
    )
    store_grade: StoreGrade | None = Field(
        default=None,
        description="门店等级。A|B|C|D",
        json_schema_extra={"example": "A"},
    )
    store_area_sqm: float | None = Field(
        default=None,
        description="门店面积。营业面积",
        json_schema_extra={"example": "120"},
    )
    biz_district: str | None = Field(
        default=None,
        description="商圈。开店甘特商圈",
        json_schema_extra={"example": "东山商圈"},
    )

class Guide(QingshuModel):
    """渠道主数据 · Guide。字段来自《标准字段定义表》。"""

    guide_id: str | None = Field(
        default=None,
        description="导购ID。导购人员ID",
        json_schema_extra={"example": "GD-1022"},
    )
    channel_account_id: str | None = Field(
        default=None,
        description="矩阵账号ID。抖音/视频号等账号",
        json_schema_extra={"example": "DY-991"},
    )
