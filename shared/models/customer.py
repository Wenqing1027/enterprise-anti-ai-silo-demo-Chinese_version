"""数据模型 · customer（由标准字段定义表生成）。"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from shared.models.base import QingshuModel
from shared.models.enums import IdentityType, IntentLevel, OneIdMatchMethod, OutreachChannel, PaidType, RenewPoolLayer, RfmSegment

class Customer(QingshuModel):
    """客户用户 · Customer。字段来自《标准字段定义表》。"""

    customer_id: str | None = Field(
        default=None,
        description="客户ID。统一客户主数据ID",
        json_schema_extra={"example": "CUS-10086"},
    )
    phone_masked: str | None = Field(
        default=None,
        description="手机号(脱敏)。脱敏手机号",
        json_schema_extra={"example": "138****5678"},
    )
    openid: str | None = Field(
        default=None,
        description="OpenID。微信OpenID",
        json_schema_extra={"example": "oxxx"},
    )
    unionid: str | None = Field(
        default=None,
        description="UnionID。微信UnionID",
        json_schema_extra={"example": "uxxx"},
    )
    identity_type: IdentityType | None = Field(
        default=None,
        description="身份类型。end_user|dealer|prospect|employee",
        json_schema_extra={"example": "end_user"},
    )
    oneid: str | None = Field(
        default=None,
        description="OneID。跨系统统一身份",
        json_schema_extra={"example": "OID-9f3a"},
    )
    oneid_match_method: OneIdMatchMethod | None = Field(
        default=None,
        description="识人匹配方式。phone|device|vin|probabilistic",
        json_schema_extra={"example": "phone"},
    )

class UserBehavior(QingshuModel):
    """客户用户 · UserBehavior。字段来自《标准字段定义表》+ 关联键。"""

    customer_id: str | None = Field(
        default=None,
        description="客户ID。关联 Customer",
        json_schema_extra={"example": "CUS-10086"},
    )
    vin: str | None = Field(
        default=None,
        description="绑车 VIN（可选）",
        json_schema_extra={"example": "LQXXXX2026A0001"},
    )
    app_register_flag: bool | None = Field(
        default=None,
        description="是否App注册。是否注册App",
        json_schema_extra={"example": "true"},
    )
    bind_vehicle_flag: bool | None = Field(
        default=None,
        description="是否绑车。是否完成绑车",
        json_schema_extra={"example": "true"},
    )
    last_active_at: datetime | None = Field(
        default=None,
        description="末次活跃时间。App/车联末次活跃",
        json_schema_extra={"example": "2026-07-20T21:00:00+08:00"},
    )
    active_days_30d: int | None = Field(
        default=None,
        description="近30天活跃天数。近30天活跃天数",
        json_schema_extra={"example": "12"},
    )
    mau_flag: bool | None = Field(
        default=None,
        description="是否计入MAU。自然月活跃标记",
        json_schema_extra={"example": "true"},
    )
    dau_flag: bool | None = Field(
        default=None,
        description="是否计入DAU。当日活跃标记",
        json_schema_extra={"example": "false"},
    )
    rfm_segment: RfmSegment | None = Field(
        default=None,
        description="RFM分群。high_value|potential|silent|churn_risk",
        json_schema_extra={"example": "high_value"},
    )
    r_days: int | None = Field(
        default=None,
        description="R值(距末活天数)。Recency",
        json_schema_extra={"example": "18"},
    )
    f_month: int | None = Field(
        default=None,
        description="F值(月互动次数)。Frequency",
        json_schema_extra={"example": "7"},
    )
    m_value: float | None = Field(
        default=None,
        description="M值(价值贡献)。配件/服务消费等",
        json_schema_extra={"example": "860"},
    )
    first_touch_channel: str | None = Field(
        default=None,
        description="首次触达渠道。首次接触渠道",
        json_schema_extra={"example": "400"},
    )
    last_touch_channel: str | None = Field(
        default=None,
        description="末次触达渠道。最近接触渠道",
        json_schema_extra={"example": "App"},
    )

class Renewal(QingshuModel):
    """客户用户 · Renewal。字段来自《标准字段定义表》+ 关联键。"""

    customer_id: str | None = Field(
        default=None,
        description="客户ID。关联 Customer",
        json_schema_extra={"example": "CUS-10086"},
    )
    vin: str | None = Field(
        default=None,
        description="车辆 VIN。关联 Vehicle",
        json_schema_extra={"example": "LQXXXX2026A0001"},
    )
    service_expire_date: date | None = Field(
        default=None,
        description="车联服务到期日。智能车服务到期",
        json_schema_extra={"example": "2026-08-15"},
    )
    due_renew_flag: bool | None = Field(
        default=None,
        description="是否到期应续费。进入应续费池",
        json_schema_extra={"example": "true"},
    )
    paid_flag: bool | None = Field(
        default=None,
        description="是否已付费。是否产生付费(需区分新购/续费)",
        json_schema_extra={"example": "false"},
    )
    paid_type: PaidType | None = Field(
        default=None,
        description="付费类型。new_purchase|renew|unknown",
        json_schema_extra={"example": "renew"},
    )
    active_t30_flag: bool | None = Field(
        default=None,
        description="到期前30天活跃。T-30活跃",
        json_schema_extra={"example": "true"},
    )
    active_t7_flag: bool | None = Field(
        default=None,
        description="到期前7天活跃。T-7活跃",
        json_schema_extra={"example": "false"},
    )
    sleep_90d_app_flag: bool | None = Field(
        default=None,
        description="近90天App沉睡。90天未用App",
        json_schema_extra={"example": "true"},
    )
    active_90d_4g_flag: bool | None = Field(
        default=None,
        description="近90天4G活跃。4G车近90天有联网",
        json_schema_extra={"example": "true"},
    )
    renew_intent_score: float | None = Field(
        default=None,
        description="续费意向分。模型/规则意向分",
        json_schema_extra={"example": "0.78"},
    )
    renew_pool_layer: RenewPoolLayer | None = Field(
        default=None,
        description="续费池分层。T-30|T-7|sleep|non_smart",
        json_schema_extra={"example": "T-30"},
    )
    outreach_channel: OutreachChannel | None = Field(
        default=None,
        description="触达渠道。push|sms|ai_call|human|wecom",
        json_schema_extra={"example": "ai_call"},
    )
    intent_level: IntentLevel | None = Field(
        default=None,
        description="外呼意向等级。high|mid|low",
        json_schema_extra={"example": "high"},
    )
