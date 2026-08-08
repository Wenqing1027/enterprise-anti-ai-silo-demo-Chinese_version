"""数据模型 · alert（由标准字段定义表生成）。"""

from __future__ import annotations

from pydantic import Field

from shared.models.base import QingshuModel
from shared.models.enums import AlertType, Severity

class Alert(QingshuModel):
    """预警协同 · Alert。字段来自《标准字段定义表》。"""

    alert_id: str | None = Field(
        default=None,
        description="预警ID。预警唯一ID",
        json_schema_extra={"example": "ALERT-20260728-014"},
    )
    alert_type: AlertType | None = Field(
        default=None,
        description="预警类型。销量下滑|合规|断货|客诉|竞品",
        json_schema_extra={"example": "shortage"},
    )
    metric_name: str | None = Field(
        default=None,
        description="触发指标名。触发指标",
        json_schema_extra={"example": "mom_rate"},
    )
    metric_value: float | None = Field(
        default=None,
        description="触发指标值。实际值",
        json_schema_extra={"example": "-12.4"},
    )
    threshold_value: float | None = Field(
        default=None,
        description="阈值。规则阈值",
        json_schema_extra={"example": "-10.0"},
    )
    severity: Severity | None = Field(
        default=None,
        description="严重级别。P0|P1|P2",
        json_schema_extra={"example": "P0"},
    )
    required_action: str | None = Field(
        default=None,
        description="要求动作。整改要求",
        json_schema_extra={"example": "3日内补色"},
    )
    verify_method: str | None = Field(
        default=None,
        description="复核方式。验收方式",
        json_schema_extra={"example": "二次巡检"},
    )

class Collab(QingshuModel):
    """预警协同 · Collab。字段来自《标准字段定义表》。"""

    cross_issue_cnt: int | None = Field(
        default=None,
        description="跨部门问题数。协同问题数",
        json_schema_extra={"example": "17"},
    )
    closed_cnt: int | None = Field(
        default=None,
        description="已闭环数。已闭环",
        json_schema_extra={"example": "9"},
    )
    overdue_cnt: int | None = Field(
        default=None,
        description="超期数。超期未闭环",
        json_schema_extra={"example": "3"},
    )
    response_hours: float | None = Field(
        default=None,
        description="响应时效。平均响应小时",
        json_schema_extra={"example": "26"},
    )
    pilot_vs_control_delta: float | None = Field(
        default=None,
        description="试点对照差。试点区vs对照区指标差",
        json_schema_extra={"example": "8.5"},
    )
    resolution_id: str | None = Field(
        default=None,
        description="决议ID。例会决议",
        json_schema_extra={"example": "RES-2026W30-01"},
    )
    owner_dept: str | None = Field(
        default=None,
        description="责任部门。责任部门",
        json_schema_extra={"example": "产品创新研究院"},
    )
    verify_metric: str | None = Field(
        default=None,
        description="回验指标。回验KPI",
        json_schema_extra={"example": "续航主题负面占比"},
    )
