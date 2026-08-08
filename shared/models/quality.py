"""数据模型 · quality（由标准字段定义表生成）。"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from shared.models.base import QingshuModel
from shared.models.enums import QcResult, RecallLevel

class Quality(QingshuModel):
    """制造质量 · Quality。字段来自《标准字段定义表》。"""

    test_station: str | None = Field(
        default=None,
        description="检测工位。质检工位",
        json_schema_extra={"example": "OBD-台架-02"},
    )
    test_ts: datetime | None = Field(
        default=None,
        description="检测时间。检测时间",
        json_schema_extra={"example": "2026-07-28T14:22:00+08:00"},
    )
    obd_protocol: str | None = Field(
        default=None,
        description="OBD协议。通信协议",
        json_schema_extra={"example": "ISO15765"},
    )
    voltage_v: float | None = Field(
        default=None,
        description="电压。检测电压",
        json_schema_extra={"example": "54.6"},
    )
    current_a: float | None = Field(
        default=None,
        description="电流。检测电流",
        json_schema_extra={"example": "12.3"},
    )
    speed_rpm: float | None = Field(
        default=None,
        description="转速。电机转速",
        json_schema_extra={"example": "480"},
    )
    controller_temp_c: float | None = Field(
        default=None,
        description="控制器温度。温升",
        json_schema_extra={"example": "46"},
    )
    qc_result: QcResult | None = Field(
        default=None,
        description="质检结果。pass|fail",
        json_schema_extra={"example": "pass"},
    )
    operator_id: str | None = Field(
        default=None,
        description="操作员工号。检测员",
        json_schema_extra={"example": "OP-331"},
    )
    part_name: str | None = Field(
        default=None,
        description="零部件名称。零部件",
        json_schema_extra={"example": "控制器"},
    )
    part_batch_no: str | None = Field(
        default=None,
        description="零部件批次。零部件批次号",
        json_schema_extra={"example": "PB-CTRL-2026W27"},
    )
    supplier_id: str | None = Field(
        default=None,
        description="供应商ID。供应商",
        json_schema_extra={"example": "SUP-8821"},
    )
    delta_e: float | None = Field(
        default=None,
        description="色差ΔE。光学色差",
        json_schema_extra={"example": "0.8"},
    )
    gloss: float | None = Field(
        default=None,
        description="光泽度。涂装光泽",
        json_schema_extra={"example": "85"},
    )
    defect_type: str | None = Field(
        default=None,
        description="缺陷类型。橘皮/色差/颗粒等",
        json_schema_extra={"example": "色差"},
    )
    anomaly_score: float | None = Field(
        default=None,
        description="设备异常分。声学/传感器异常",
        json_schema_extra={"example": "0.86"},
    )
    predict_fail_days: int | None = Field(
        default=None,
        description="预计故障天数。预测性维护窗口",
        json_schema_extra={"example": "14"},
    )
    release_ts: datetime | None = Field(
        default=None,
        description="放行时间。合格放行",
        json_schema_extra={"example": "2026-07-28T16:00:00+08:00"},
    )
    trace_package_url: str | None = Field(
        default=None,
        description="追溯包地址。追溯数据包",
        json_schema_extra={"example": "s3://trace/VINxxx.zip"},
    )
    recall_level: RecallLevel | None = Field(
        default=None,
        description="召回评估等级。watch|targeted|recall_eval",
        json_schema_extra={"example": "watch"},
    )
