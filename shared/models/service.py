"""数据模型 · service（由标准字段定义表生成）。"""

from __future__ import annotations

from datetime import datetime

from typing import Any

from pydantic import Field

from shared.models.base import QingshuModel
from shared.models.enums import ClueConfidence, CoverDim, FaultCategory, ModuleName, Sentiment, SopPassFail, TagDomain, TicketStatus, TicketType

class Ticket(QingshuModel):
    """工单服务 · Ticket。字段来自《标准字段定义表》+ 关联键。"""

    ticket_id: str | None = Field(
        default=None,
        description="工单ID。工单唯一ID",
        json_schema_extra={"example": "TK-20260728-8891"},
    )
    customer_id: str | None = Field(
        default=None,
        description="客户ID。关联 Customer",
        json_schema_extra={"example": "CUS-10086"},
    )
    vin: str | None = Field(
        default=None,
        description="车架号VIN。关联 Vehicle",
        json_schema_extra={"example": "LQXXXX2026A0001"},
    )
    store_id: str | None = Field(
        default=None,
        description="门店ID。关联 Store（可选）",
        json_schema_extra={"example": "ST-8891"},
    )
    dealer_id: str | None = Field(
        default=None,
        description="经销商ID。关联 Dealer（可选）",
        json_schema_extra={"example": "DLR-3201"},
    )
    tag_id: str | None = Field(
        default=None,
        description="主标签ID。关联 TagVocabulary",
        json_schema_extra={"example": "TAG-续航短"},
    )
    sentiment: Sentiment | None = Field(
        default=None,
        description="情感极性。打标结果",
        json_schema_extra={"example": "neg"},
    )
    ticket_type: TicketType | None = Field(
        default=None,
        description="工单类型。fault|consult|complaint|other",
        json_schema_extra={"example": "fault"},
    )
    fault_category: FaultCategory | None = Field(
        default=None,
        description="故障大类。电池|电机|刹车|控制器|充电|仪表|车架|灯具|轮胎|其他",
        json_schema_extra={"example": "battery"},
    )
    consult_category: str | None = Field(
        default=None,
        description="咨询大类。咨询分类",
        json_schema_extra={"example": "整车信息"},
    )
    ticket_channel: str | None = Field(
        default=None,
        description="工单渠道。400|App|电商|门店",
        json_schema_extra={"example": "400"},
    )
    ticket_status: TicketStatus | None = Field(
        default=None,
        description="工单状态。open|processing|closed",
        json_schema_extra={"example": "open"},
    )
    ticket_created_at: datetime | None = Field(
        default=None,
        description="工单创建时间。创建时间",
        json_schema_extra={"example": "2026-07-28T09:12:00+08:00"},
    )
    handle_duration_min: float | None = Field(
        default=None,
        description="处理时长。处理耗时",
        json_schema_extra={"example": "18"},
    )
    is_complaint: bool | None = Field(
        default=None,
        description="是否投诉。投诉标记",
        json_schema_extra={"example": "true"},
    )
    three_guarantees_reject_flag: bool | None = Field(
        default=None,
        description="三包拒保标记。三包拒保",
        json_schema_extra={"example": "false"},
    )
    desc_text: str | None = Field(
        default=None,
        description="问题描述文本。原声/描述",
        json_schema_extra={"example": "骑行续航明显低于标称"},
    )
    desc_chars: int | None = Field(
        default=None,
        description="描述字数。描述长度",
        json_schema_extra={"example": "86"},
    )
    transcript_text: str | None = Field(
        default=None,
        description="转写文本。语音转写结果",
        json_schema_extra={"example": "（通话转写全文）"},
    )
    agent_id: str | None = Field(
        default=None,
        description="坐席/外呼员ID。客服/外呼人员",
        json_schema_extra={"example": "AG-2201"},
    )
    sop_item: str | None = Field(
        default=None,
        description="SOP质检项。质检项",
        json_schema_extra={"example": "是否确认VIN与车型"},
    )
    sop_pass_fail: SopPassFail | None = Field(
        default=None,
        description="SOP是否通过。pass|fail",
        json_schema_extra={"example": "pass"},
    )
    risk_words: Any | None = Field(
        default=None,
        description="风险话术词。质检风险词",
    )

class VoC(QingshuModel):
    """工单服务 · VoC。字段来自《标准字段定义表》。"""

    feedback_id: str | None = Field(
        default=None,
        description="反馈ID。VoC反馈唯一ID",
        json_schema_extra={"example": "FB-99102"},
    )
    nps: float | None = Field(
        default=None,
        description="NPS。净推荐值",
        json_schema_extra={"example": "32"},
    )
    csat: float | None = Field(
        default=None,
        description="CSAT。满意度1-5",
        json_schema_extra={"example": "4.1"},
    )
    nps_delta: float | None = Field(
        default=None,
        description="NPS变化。周期NPS变化",
        json_schema_extra={"example": "-3"},
    )
    feedback_cnt: int | None = Field(
        default=None,
        description="反馈量。周期反馈条数",
        json_schema_extra={"example": "1280"},
    )
    tag_id: str | None = Field(
        default=None,
        description="标签ID。标准标签ID",
        json_schema_extra={"example": "TAG-续航短"},
    )
    tag_name: str | None = Field(
        default=None,
        description="标签名称。标签名",
        json_schema_extra={"example": "续航短"},
    )
    tag_domain: TagDomain | None = Field(
        default=None,
        description="标签域。product|service|app|channel|risk",
        json_schema_extra={"example": "product"},
    )
    sentiment: Sentiment | None = Field(
        default=None,
        description="情感极性。pos|neu|neg",
        json_schema_extra={"example": "neg"},
    )
    sentiment_score: float | None = Field(
        default=None,
        description="情感分数。情感强度",
        json_schema_extra={"example": "-0.72"},
    )
    problem_theme: str | None = Field(
        default=None,
        description="问题主题。主题聚类名",
        json_schema_extra={"example": "续航短"},
    )
    theme_cnt: int | None = Field(
        default=None,
        description="主题反馈量。主题计数",
        json_schema_extra={"example": "246"},
    )
    neg_ratio: float | None = Field(
        default=None,
        description="负面占比。主题负面占比",
        json_schema_extra={"example": "68.0"},
    )
    wow_change: float | None = Field(
        default=None,
        description="周环比变化。周变化",
        json_schema_extra={"example": "22.0"},
    )
    closed_loop_rate: float | None = Field(
        default=None,
        description="闭环率。已闭环/应闭环",
        json_schema_extra={"example": "54.0"},
    )
    recurrence_rate: float | None = Field(
        default=None,
        description="复发率。复发占比",
        json_schema_extra={"example": "12.0"},
    )
    cover_dim: CoverDim | None = Field(
        default=None,
        description="报告封面维度。vehicle|non_vehicle|all",
        json_schema_extra={"example": "vehicle"},
    )
    module_name: ModuleName | None = Field(
        default=None,
        description="非车板块。app|miniapp|website|hotline|aftersales",
        json_schema_extra={"example": "app"},
    )
    sample_voice: str | None = Field(
        default=None,
        description="代表性原声。脱敏原声",
        json_schema_extra={"example": "充满电跑不到说明书一半"},
    )
    clue_confidence: ClueConfidence | None = Field(
        default=None,
        description="线索置信度。weak|medium",
        json_schema_extra={"example": "medium"},
    )
    severity_risk_level: str | None = Field(
        default=None,
        description="舆情/公关风险等级。P0|P1|P2",
        json_schema_extra={"example": "P1"},
    )
    consumer_sat_score: float | None = Field(
        default=None,
        description="消费者满意度。调研消费者满意度",
        json_schema_extra={"example": "82.9"},
    )
    channel_sat_score: float | None = Field(
        default=None,
        description="渠道满意度。调研渠道满意度",
        json_schema_extra={"example": "77.1"},
    )
    survey_recover_rate: float | None = Field(
        default=None,
        description="问卷回收率。回收/推送",
        json_schema_extra={"example": "6.1"},
    )
    dissatisfaction_reason: str | None = Field(
        default=None,
        description="不满原因。开放题/选项原因",
        json_schema_extra={"example": "续航短"},
    )
