"""数据模型 · vehicle（由标准字段定义表生成）。"""

from __future__ import annotations

from datetime import date

from pydantic import Field

from shared.models.base import QingshuModel
from shared.models.enums import BatteryType

class Vehicle(QingshuModel):
    """车辆 · Vehicle。字段来自《标准字段定义表》。"""

    vin: str | None = Field(
        default=None,
        description="车架号VIN。整车唯一识别",
        json_schema_extra={"example": "LQXXXX2026A0001"},
    )
    frame_no: str | None = Field(
        default=None,
        description="车架件号。PDA绑定车架件",
        json_schema_extra={"example": "FR-778812"},
    )
    sn: str | None = Field(
        default=None,
        description="整车序列号。产线序列号",
        json_schema_extra={"example": "SN-202607-8891"},
    )
    vehicle_model: str | None = Field(
        default=None,
        description="车型。车型编码/名",
        json_schema_extra={"example": "E60"},
    )
    vehicle_config: str | None = Field(
        default=None,
        description="配置类型。配置档",
        json_schema_extra={"example": "锂电旗舰"},
    )
    color: str | None = Field(
        default=None,
        description="颜色。车身颜色",
        json_schema_extra={"example": "哑光黑"},
    )
    battery_type: BatteryType | None = Field(
        default=None,
        description="电池类型。lead_acid|lithium|graphene",
        json_schema_extra={"example": "lithium"},
    )
    battery_spec: str | None = Field(
        default=None,
        description="电池规格。电压安时",
        json_schema_extra={"example": "48V24Ah"},
    )
    claimed_range_km: float | None = Field(
        default=None,
        description="标称续航。官方续航",
        json_schema_extra={"example": "80"},
    )
    purchase_date: date | None = Field(
        default=None,
        description="购车日期。用户购车日",
        json_schema_extra={"example": "2025-08-01"},
    )
    purchase_year: int | None = Field(
        default=None,
        description="购车年份。购车年",
        json_schema_extra={"example": "2025"},
    )
    is_smart_vehicle: bool | None = Field(
        default=None,
        description="是否智能车。是否具备4G/车联",
        json_schema_extra={"example": "true"},
    )
    plant: str | None = Field(
        default=None,
        description="生产基地。制造基地",
        json_schema_extra={"example": "华东一厂"},
    )
    line_id: str | None = Field(
        default=None,
        description="产线ID。产线",
        json_schema_extra={"example": "LINE-03"},
    )
    batch_no: str | None = Field(
        default=None,
        description="整车生产批次。整车批次",
        json_schema_extra={"example": "BATCH-2026W28-E60"},
    )
    ota_version: str | None = Field(
        default=None,
        description="OTA版本。车端软件版本",
        json_schema_extra={"example": "v2.3.1"},
    )
    customer_id: str | None = Field(
        default=None,
        description="客户ID。关联 Customer",
        json_schema_extra={"example": "CUS-10086"},
    )
    store_id: str | None = Field(
        default=None,
        description="门店ID。购车/绑车门店（可选）",
        json_schema_extra={"example": "ST-8891"},
    )
