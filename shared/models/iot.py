"""数据模型 · iot（由标准字段定义表生成）。"""

from __future__ import annotations

from pydantic import Field

from shared.models.base import QingshuModel

class Telemetry(QingshuModel):
    """车联IoT · Telemetry。字段来自《标准字段定义表》+ 关联键。"""

    vin: str | None = Field(
        default=None,
        description="车架号VIN。关联 Vehicle",
        json_schema_extra={"example": "LQXXXX2026A0001"},
    )

    fault_code: str | None = Field(
        default=None,
        description="故障码/告警码。车端告警码",
        json_schema_extra={"example": "BMS_OT_01"},
    )
    iot_alert_cnt: int | None = Field(
        default=None,
        description="告警次数。周期告警次数",
        json_schema_extra={"example": "3"},
    )
    mileage_km: float | None = Field(
        default=None,
        description="里程。累计/周期里程",
        json_schema_extra={"example": "3260"},
    )
    soc_pct: float | None = Field(
        default=None,
        description="电量SOC。剩余电量",
        json_schema_extra={"example": "64"},
    )
    telemetry_coverage_rate: float | None = Field(
        default=None,
        description="回传覆盖率。有telemetry车辆占比",
        json_schema_extra={"example": "81.0"},
    )
    battery_health_pct: float | None = Field(
        default=None,
        description="电池健康度。SOH近似",
        json_schema_extra={"example": "92"},
    )
