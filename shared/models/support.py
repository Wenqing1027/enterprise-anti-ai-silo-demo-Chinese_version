"""数据模型 · support（由标准字段定义表生成）。"""

from __future__ import annotations

from pydantic import Field

from shared.models.base import QingshuModel
from shared.models.enums import ClauseRiskLevel, KbDomain, ProposalLevel

class Process(QingshuModel):
    """流程人资法务 · Process。字段来自《标准字段定义表》。"""

    process_id: str | None = Field(
        default=None,
        description="流程ID。流程定义ID",
        json_schema_extra={"example": "PROC-开店审批"},
    )
    redundant_step: str | None = Field(
        default=None,
        description="冗余环节。冗余检测",
        json_schema_extra={"example": "重复盖章节点"},
    )
    bottleneck_step: str | None = Field(
        default=None,
        description="卡点环节。根因诊断",
        json_schema_extra={"example": "额度审批"},
    )
    cycle_time_hours: float | None = Field(
        default=None,
        description="周期时长。流程耗时",
        json_schema_extra={"example": "72"},
    )
    proposal_level: ProposalLevel | None = Field(
        default=None,
        description="建议级别。L1|L2|L3",
        json_schema_extra={"example": "L2"},
    )

class HR(QingshuModel):
    """流程人资法务 · HR。字段来自《标准字段定义表》。"""

    job_id: str | None = Field(
        default=None,
        description="岗位ID。招聘岗位",
        json_schema_extra={"example": "JOB-售后专员"},
    )
    match_score: float | None = Field(
        default=None,
        description="人岗匹配分。匹配得分",
        json_schema_extra={"example": "84"},
    )

class Legal(QingshuModel):
    """流程人资法务 · Legal。字段来自《标准字段定义表》。"""

    contract_id: str | None = Field(
        default=None,
        description="合同ID。合同编号",
        json_schema_extra={"example": "CT-2026-889"},
    )
    clause_risk_level: ClauseRiskLevel | None = Field(
        default=None,
        description="条款风险等级。low|medium|high",
        json_schema_extra={"example": "high"},
    )
    clause_comment: str | None = Field(
        default=None,
        description="审核意见。合同审核意见",
        json_schema_extra={"example": "违约金上限缺失"},
    )

class Knowledge(QingshuModel):
    """流程人资法务 · Knowledge。字段来自《标准字段定义表》。"""

    kb_domain: KbDomain | None = Field(
        default=None,
        description="知识库域。repair|policy|hr|product",
        json_schema_extra={"example": "repair"},
    )
    kb_doc_id: str | None = Field(
        default=None,
        description="知识文档ID。文档ID",
        json_schema_extra={"example": "KB-REP-0012"},
    )
    kb_chunk_id: str | None = Field(
        default=None,
        description="知识片段ID。向量片段ID",
        json_schema_extra={"example": "CHK-88"},
    )
    kb_score: float | None = Field(
        default=None,
        description="检索相关分。检索得分",
        json_schema_extra={"example": "0.83"},
    )
