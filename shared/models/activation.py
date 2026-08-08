"""数据模型 · activation（由标准字段定义表生成）。"""

from __future__ import annotations

from pydantic import Field

from shared.models.base import QingshuModel

class Activation(QingshuModel):
    """App激活 · Activation。字段来自《标准字段定义表》。"""

    cum_sales_units: int | None = Field(
        default=None,
        description="累计销量。累计整车销量",
        json_schema_extra={"example": "2500000"},
    )
    active_owners_est: int | None = Field(
        default=None,
        description="在用车主估计。在用车主",
        json_schema_extra={"example": "1800000"},
    )
    app_register_cnt: int | None = Field(
        default=None,
        description="App注册数。注册用户数",
        json_schema_extra={"example": "920000"},
    )
    bind_vehicle_cnt: int | None = Field(
        default=None,
        description="绑车数。完成绑车数",
        json_schema_extra={"example": "610000"},
    )
    mau: int | None = Field(
        default=None,
        description="月活MAU。月活跃",
        json_schema_extra={"example": "210000"},
    )
    dau: int | None = Field(
        default=None,
        description="日活DAU。日活跃",
        json_schema_extra={"example": "42000"},
    )
    activation_rate: float | None = Field(
        default=None,
        description="激活率。绑车/在用车主等口径",
        json_schema_extra={"example": "33.9"},
    )
    funnel_step: str | None = Field(
        default=None,
        description="漏斗步骤。打开→登录→绑车→车控→留存",
        json_schema_extra={"example": "绑车"},
    )
    funnel_uv: int | None = Field(
        default=None,
        description="步骤UV。步骤独立用户",
        json_schema_extra={"example": "88000"},
    )
    funnel_cvr: float | None = Field(
        default=None,
        description="步骤转化率。到下一步转化",
        json_schema_extra={"example": "62.0"},
    )
    tab_name: str | None = Field(
        default=None,
        description="App Tab名。功能Tab",
        json_schema_extra={"example": "用车"},
    )
    pv: int | None = Field(
        default=None,
        description="PV。页面浏览",
        json_schema_extra={"example": "560000"},
    )
    uv: int | None = Field(
        default=None,
        description="UV。独立访客",
        json_schema_extra={"example": "120000"},
    )
    stay_seconds: float | None = Field(
        default=None,
        description="停留秒数。停留时长",
        json_schema_extra={"example": "46"},
    )
    push_click_rate: float | None = Field(
        default=None,
        description="Push点击率。Push CTR",
        json_schema_extra={"example": "8.6"},
    )
    faq_cnt: int | None = Field(
        default=None,
        description="FAQ条目数。知识库条目",
        json_schema_extra={"example": "320"},
    )
    top20_ticket_coverage_rate: float | None = Field(
        default=None,
        description="Top20工单覆盖率。FAQ覆盖高频工单",
        json_schema_extra={"example": "71.0"},
    )
    oneid_coverage_rate: float | None = Field(
        default=None,
        description="OneID覆盖率。可识别用户占比",
        json_schema_extra={"example": "64.0"},
    )
    orphan_user_cnt: int | None = Field(
        default=None,
        description="孤岛用户数。无法缝合用户",
        json_schema_extra={"example": "120000"},
    )
    koc_score: float | None = Field(
        default=None,
        description="KOC得分。社区KOC评分",
        json_schema_extra={"example": "81"},
    )
    post_cnt: int | None = Field(
        default=None,
        description="发帖数。社区发帖",
        json_schema_extra={"example": "24"},
    )
    interact_rate: float | None = Field(
        default=None,
        description="互动率。互动/曝光",
        json_schema_extra={"example": "6.8"},
    )

class O2O(QingshuModel):
    """App激活 · O2O。字段来自《标准字段定义表》。"""

    platform_order_cnt: int | None = Field(
        default=None,
        description="平台订单数。电商平台订单",
        json_schema_extra={"example": "1500"},
    )
    lead_phone_cnt: int | None = Field(
        default=None,
        description="留资手机号数。留资数",
        json_schema_extra={"example": "980"},
    )
    store_redeem_cnt: int | None = Field(
        default=None,
        description="到店核销数。到店核销",
        json_schema_extra={"example": "420"},
    )
