"""数据模型 · retail（由标准字段定义表生成）。"""

from __future__ import annotations

from pydantic import Field

from shared.models.base import QingshuModel

class Retail(QingshuModel):
    """零售营销 · Retail。字段来自《标准字段定义表》。"""

    retail_qty: int | None = Field(
        default=None,
        description="零售台数。输卡/零售量",
        json_schema_extra={"example": "46"},
    )
    retail_qty_day: int | None = Field(
        default=None,
        description="当日零售。日零售",
        json_schema_extra={"example": "6"},
    )
    retail_qty_mtd: int | None = Field(
        default=None,
        description="月累计零售。月零售",
        json_schema_extra={"example": "142"},
    )
    retail_yoy: float | None = Field(
        default=None,
        description="零售同比。零售同比",
        json_schema_extra={"example": "8.2"},
    )
    writeoff_qty: int | None = Field(
        default=None,
        description="核销数量。活动核销台数",
        json_schema_extra={"example": "28"},
    )
    redeem_rate: float | None = Field(
        default=None,
        description="核销率。核销/应核销",
        json_schema_extra={"example": "62.0"},
    )
    gross_margin_amt: float | None = Field(
        default=None,
        description="毛利额。毛利金额",
        json_schema_extra={"example": "9860"},
    )
    gross_margin_rate: float | None = Field(
        default=None,
        description="毛利率。毛利率",
        json_schema_extra={"example": "17.9"},
    )
    non_exclusive_rate: float | None = Field(
        default=None,
        description="非专卖率。混营/非专卖占比",
        json_schema_extra={"example": "0"},
    )
    non_exclusive_flag: bool | None = Field(
        default=None,
        description="非专卖标记。是否非专卖门店",
        json_schema_extra={"example": "false"},
    )

class Campaign(QingshuModel):
    """零售营销 · Campaign。字段来自《标准字段定义表》。"""

    campaign_id: str | None = Field(
        default=None,
        description="活动ID。营销活动ID",
        json_schema_extra={"example": "CAMP-暑期换新"},
    )
    campaign_name: str | None = Field(
        default=None,
        description="活动名称。活动名",
        json_schema_extra={"example": "暑期以旧换新"},
    )
    campaign_goal: str | None = Field(
        default=None,
        description="活动目标。活动目标",
        json_schema_extra={"example": "提升续费转化"},
    )
    campaign_budget: float | None = Field(
        default=None,
        description="活动预算。预算",
        json_schema_extra={"example": "50000"},
    )
    participants: int | None = Field(
        default=None,
        description="参与人数。参与人数",
        json_schema_extra={"example": "3200"},
    )
    campaign_roi: float | None = Field(
        default=None,
        description="活动ROI。投入产出比",
        json_schema_extra={"example": "2.4"},
    )
    campaign_complaint_rate: float | None = Field(
        default=None,
        description="活动投诉率。活动相关投诉率",
        json_schema_extra={"example": "0.3"},
    )

class Content(QingshuModel):
    """零售营销 · Content。字段来自《标准字段定义表》。"""

    short_video_cnt: int | None = Field(
        default=None,
        description="短视频数。短视频产量",
        json_schema_extra={"example": "2140"},
    )
    short_video_valid_participate_rate: float | None = Field(
        default=None,
        description="短视频有效参与率。有效参与占比",
        json_schema_extra={"example": "38.5"},
    )
    followers: int | None = Field(
        default=None,
        description="粉丝数。账号粉丝",
        json_schema_extra={"example": "12400"},
    )
    play_cnt: int | None = Field(
        default=None,
        description="播放量。播放量",
        json_schema_extra={"example": "86000"},
    )
    gmv_convert_rate: float | None = Field(
        default=None,
        description="带货转化率。播放→成交",
        json_schema_extra={"example": "1.8"},
    )
    deals_cnt: int | None = Field(
        default=None,
        description="成交单数。导购成交数",
        json_schema_extra={"example": "36"},
    )
    gmv: float | None = Field(
        default=None,
        description="成交额GMV。成交额",
        json_schema_extra={"example": "118764"},
    )
    aov: float | None = Field(
        default=None,
        description="客单价。笔单价",
        json_schema_extra={"example": "3299"},
    )
    valid_seller_flag: bool | None = Field(
        default=None,
        description="是否有效带货账号。有效带货判定",
        json_schema_extra={"example": "true"},
    )
    live_sessions: int | None = Field(
        default=None,
        description="直播场次。直播场次",
        json_schema_extra={"example": "12"},
    )
    live_watch_uv: int | None = Field(
        default=None,
        description="直播观看UV。直播观看人数",
        json_schema_extra={"example": "5600"},
    )
    influencer_cvr: float | None = Field(
        default=None,
        description="达人转化率。达人带货转化",
        json_schema_extra={"example": "2.1"},
    )
    refund_rate: float | None = Field(
        default=None,
        description="退款率。退款占比",
        json_schema_extra={"example": "1.2"},
    )
    content_script_id: str | None = Field(
        default=None,
        description="脚本/素材ID。内容资产ID",
        json_schema_extra={"example": "SCRIPT-续航对比-01"},
    )
    benchmark_case_id: str | None = Field(
        default=None,
        description="标杆案例ID。标杆案例",
        json_schema_extra={"example": "CASE-苏州吴中店"},
    )

class Outreach(QingshuModel):
    """零售营销 · Outreach。字段来自《标准字段定义表》。"""

    channel_quota_daily: int | None = Field(
        default=None,
        description="渠道日配额。触达日配额",
        json_schema_extra={"example": "5000"},
    )
    delivery_rate: float | None = Field(
        default=None,
        description="到达率。消息到达率",
        json_schema_extra={"example": "96.2"},
    )
    open_rate: float | None = Field(
        default=None,
        description="打开率。打开/点击率",
        json_schema_extra={"example": "28.4"},
    )
    connect_rate: float | None = Field(
        default=None,
        description="接通率。外呼接通率",
        json_schema_extra={"example": "41.0"},
    )
    transfer_human_cnt: int | None = Field(
        default=None,
        description="转人工数。高意向转人工",
        json_schema_extra={"example": "86"},
    )
    template_approve_days: float | None = Field(
        default=None,
        description="模板审核周期。审核天数",
        json_schema_extra={"example": "2"},
    )
