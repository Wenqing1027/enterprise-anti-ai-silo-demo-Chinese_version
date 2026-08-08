"""业务平台目录：部门 × 角色 × 功能（全量展示；demo_ready 可跑）。

V2 口径：agent_type 主值 = 平台控制环 retrieve|act|extract|plan。
历史名 rag|react|extraction|planning 见 apps.loops 别名表（查询仍兼容）。
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from apps.loops import (
    PLATFORM_LOOPS,
    build_agent_types,
    canonicalize,
    display_name,
    same_loop,
)

_ROOT = Path(__file__).resolve().parents[1]
_FLOWS_PATH = _ROOT / "data" / "entities" / "department_flows.json"

# ---------------------------------------------------------------------------
# Agent 类型（运维侧按 4 环分治；业务侧聚合展示）
# ---------------------------------------------------------------------------

AGENT_TYPES: list[dict[str, Any]] = build_agent_types()

# ---------------------------------------------------------------------------
# 部门 + 角色
# ---------------------------------------------------------------------------

DEPARTMENTS: dict[str, dict[str, Any]] = {
    "service": {
        "department_id": "service",
        "name": "服务事业部",
        "tone_label": "稳妥确认型",
        "roles": [
            {"role_id": "agent", "name": "400/坐席"},
            {"role_id": "supervisor", "name": "班组长"},
        ],
    },
    "user_ops": {
        "department_id": "user_ops",
        "name": "用户运营 / App",
        "tone_label": "促而不逼型",
        "roles": [
            {"role_id": "renewal_ops", "name": "续费运营"},
            {"role_id": "app_cs", "name": "App 客服运营"},
        ],
    },
    "order_policy": {
        "department_id": "order_policy",
        "name": "运营管理 · 订单/政策",
        "tone_label": "口径严谨型",
        "roles": [
            {"role_id": "order_clerk", "name": "审单专员"},
            {"role_id": "policy_analyst", "name": "政策分析"},
        ],
    },
    "warzone": {
        "department_id": "warzone",
        "name": "四大战区",
        "tone_label": "前线干脆型",
        "roles": [
            {"role_id": "bd", "name": "战区 BD"},
            {"role_id": "manager", "name": "战区经理"},
        ],
    },
    "channel": {
        "department_id": "channel",
        "name": "渠道处",
        "tone_label": "经营看板型",
        "roles": [
            {"role_id": "specialist", "name": "渠道专员"},
            {"role_id": "manager", "name": "渠道经理"},
        ],
    },
    "retail": {
        "department_id": "retail",
        "name": "新零售",
        "tone_label": "货架导购型",
        "roles": [
            {"role_id": "cs", "name": "平台客服"},
            {"role_id": "ops", "name": "零售运营"},
        ],
    },
    "procurement": {
        "department_id": "procurement",
        "name": "采购平台",
        "tone_label": "节点追踪型",
        "roles": [
            {"role_id": "buyer", "name": "采购跟单"},
            {"role_id": "lead", "name": "采购主管"},
        ],
    },
    "data_lab": {
        "department_id": "data_lab",
        "name": "数据研究院",
        "tone_label": "结论优先型",
        "roles": [
            {"role_id": "analyst", "name": "业务分析师"},
            {"role_id": "steward", "name": "指标管理员"},
        ],
    },
    "hr": {
        "department_id": "hr",
        "name": "人资管理平台",
        "tone_label": "友好中立型",
        "roles": [
            {"role_id": "employee", "name": "员工自助"},
            {"role_id": "hrbp", "name": "HRBP"},
        ],
    },
    "iot": {
        "department_id": "iot",
        "name": "IoT / 车机",
        "tone_label": "告警简报型",
        "roles": [
            {"role_id": "ops", "name": "车联运营"},
            {"role_id": "quality", "name": "质量联动"},
        ],
    },
    "voc": {
        "department_id": "voc",
        "name": "用研 / VoC",
        "tone_label": "中性标注腔",
        "roles": [
            {"role_id": "analyst", "name": "用研分析"},
            {"role_id": "ops", "name": "VoC 运营"},
        ],
    },
    "shared": {
        "department_id": "shared",
        "name": "跨部门共用 / 共享层",
        "tone_label": "中性系统腔",
        "roles": [
            {"role_id": "consumer", "name": "业务消费方"},
            {"role_id": "integrator", "name": "集成对接"},
        ],
    },
}

# ---------------------------------------------------------------------------
# ReAct 功能全量（含未一期实现；demo_ready=True 可直接跑）
# ---------------------------------------------------------------------------

FEATURES: list[dict[str, Any]] = [
    # 服务
    {
        "feature_id": "F-SVC-001",
        "name": "智能填单",
        "purpose": "对话生成工单草案并写入共享产出",
        "department_id": "service",
        "roles": ["agent", "supervisor"],
        "agent_type": "act",
        "skill_id": "fill_ticket",
        "demo_ready": True,
        "status": "demo",
        "phase": "demo",
        "layout": "ticket",
        "input_fields": ["text", "customer_id", "vin", "channel"],
        "sample": {
            "text": "投诉门店未按三包政策处理电池更换，工单已超过7天未结。",
            "customer_id": "CUS-10057",
            "vin": "QS0F65B984410D7B6",
            "channel": "400",
        },
        "placeholder_text": "描述客户问题…",
        "story": "Story1",
        "flow_ids": ["service_ticket_to_shared", "story2_outreach_gate"],
        "note": "【ReAct · fill_ticket】与 F-SVC-001-EXT（Extraction · ticket_fields）并行可选，同一 Story1 目标。本卡走 POST /v1/react/runs；内置工具 extract_ticket_fields 是规则抽字段，不是 Extraction Agent。",
        "orchestration": "parallel_alt",
    },
    {
        "feature_id": "F-SVC-001-EXT",
        "name": "智能填单 · Extraction",
        "purpose": "纯结构化抽取工单草案并写入共享产出",
        "department_id": "service",
        "roles": ["agent", "supervisor"],
        "agent_type": "extract",
        "skill_id": "ticket_fields",
        "demo_ready": True,
        "status": "demo",
        "phase": "demo",
        "layout": "extract",
        "input_fields": ["text", "customer_id", "vin", "channel"],
        "sample": {
            "text": "投诉门店未按三包政策处理电池更换，工单已超过7天未结。",
            "customer_id": "CUS-10057",
            "vin": "QS0F65B984410D7B6",
            "channel": "400",
        },
        "placeholder_text": "粘贴客服对话/转写…",
        "story": "Story1-Extraction",
        "flow_ids": ["service_ticket_to_shared", "story2_outreach_gate"],
        "note": "【Extraction · ticket_fields】与 F-SVC-001（ReAct · fill_ticket）并行可选；API=POST /v1/extraction/runs。产出可供 Story2 续费闸门串行消费。",
        "orchestration": "parallel_alt",
    },
    {
        "feature_id": "F-SVC-002",
        "name": "智能辅助回答 · RAG",
        "purpose": "坐席侧维修知识问答，并标注参考资料",
        "department_id": "service",
        "roles": ["agent", "supervisor"],
        "agent_type": "retrieve",
        "skill_id": "repair_kb",
        "demo_ready": True,
        "status": "demo",
        "phase": "demo",
        "layout": "rag",
        "input_fields": ["query"],
        "sample": {"query": "续航低于标称怎么排查？"},
        "placeholder_text": "输入维修/售后问题…",
        "flow_ids": ["service_repair_qa"],
        "note": "【RAG · repair_kb】与 Story1 填单并行存在；API=POST /v1/rag/runs。",
        "orchestration": "parallel_orthogonal",
    },
    {
        "feature_id": "F-SVC-004",
        "name": "维修知识库问答",
        "purpose": "维修问题自助/辅助问答",
        "department_id": "service",
        "roles": ["agent", "supervisor"],
        "agent_type": "retrieve",
        "skill_id": "repair_kb",
        "demo_ready": True,
        "status": "demo",
        "phase": "demo",
        "layout": "rag",
        "input_fields": ["query"],
        "sample": {"query": "App 绑车失败怎么办？"},
        "placeholder_text": "输入维修问题…",
        "flow_ids": ["service_repair_qa"],
        "note": "与 F-SVC-002 同 Skill repair_kb",
        "orchestration": "parallel_orthogonal",
    },
    {
        "feature_id": "F-POL-RAG",
        "name": "政策口径问答 · RAG",
        "purpose": "三包/返利/续费红线等政策文本问答",
        "department_id": "order_policy",
        "roles": ["policy_analyst", "order_clerk"],
        "agent_type": "retrieve",
        "skill_id": "policy_kb",
        "demo_ready": True,
        "status": "demo",
        "phase": "demo",
        "layout": "rag",
        "input_fields": ["query"],
        "sample": {"query": "2026Q3 提货返利金牌要提多少台？"},
        "placeholder_text": "输入政策问题…",
        "flow_ids": ["order_policy_qa", "channel_ops_board"],
        "note": "【RAG · policy_kb】与审单串行链并行可选；亦可与渠道 channel_ops 并行准备看板口径。不替代 Rule 闸门。",
        "orchestration": "parallel_optional",
    },
    {
        "feature_id": "F-UO-009",
        "name": "App 智能问答 MVP",
        "purpose": "App 内维修/使用问答（复用 repair 域）",
        "department_id": "user_ops",
        "roles": ["app_cs"],
        "agent_type": "retrieve",
        "skill_id": "repair_kb",
        "demo_ready": True,
        "status": "demo",
        "phase": "demo",
        "layout": "rag",
        "input_fields": ["query"],
        "sample": {"query": "充电口接触不良怎么处理？"},
        "placeholder_text": "输入用户问题…",
        "flow_ids": ["user_ops_app_qa"],
        "note": "一期复用 repair_kb，与续费闸门无关并行",
        "orchestration": "parallel_orthogonal",
    },
    {
        "feature_id": "F-VOC-002",
        "name": "客户原声整理",
        "purpose": "把客户原声整理成业务标记、情绪与风险提示",
        "department_id": "voc",
        "roles": ["analyst", "ops"],
        "agent_type": "extract",
        "skill_id": "voc_entities",
        "demo_ready": True,
        "status": "demo",
        "phase": "demo",
        "layout": "extract",
        "input_fields": ["text", "customer_id", "vin"],
        "sample": {
            "text": "充满电跑不到说明书一半，准备去媒体曝光。",
            "customer_id": "CUS-10057",
        },
        "placeholder_text": "粘贴客户原声…",
        "story": "Story1-Extraction",
        "flow_ids": ["voc_entities_to_shared", "story2_outreach_gate"],
        "note": "与服务填单跨部门并行写共享；含阻断标签时成为 Story2 上游",
        "orchestration": "parallel_producer",
    },
    {
        "feature_id": "F-SVC-005",
        "name": "VOC 故障聚类",
        "purpose": "工单聚类后反哺产品/质量洞察",
        "department_id": "service",
        "roles": ["supervisor"],
        "agent_type": "extract",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase2",
        "layout": "extract",
        "note": "展示：串行依赖 F-VOC-002 条级打标之后；一期不跑控制环",
        "orchestration": "sequence_downstream",
        "flow_ids": ["voc_entities_to_shared"],
    },
    {
        "feature_id": "F-SVC-008",
        "name": "智能质检（SOP）",
        "purpose": "录音转写 → SOP 合规抽取",
        "department_id": "service",
        "roles": ["supervisor"],
        "agent_type": "extract",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase3",
        "layout": "extract",
        "note": "展示：可与填单并行的 Extraction 能力；需转写前置",
        "orchestration": "parallel_showcase",
    },
    {
        "feature_id": "F-OPS-004",
        "name": "销售政策解析",
        "purpose": "政策原文 → 返利档位结构",
        "department_id": "order_policy",
        "roles": ["policy_analyst"],
        "agent_type": "extract",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase2",
        "layout": "extract",
        "note": "展示：串行上游 → Rule+LLM 档位闸门（见 order_policy_review）",
        "orchestration": "sequence_upstream",
        "flow_ids": ["order_policy_review"],
    },
    {
        "feature_id": "F-FIN-001",
        "name": "智能报销 · 三单匹配抽取",
        "purpose": "发票/合同/入库单字段抽取",
        "department_id": "shared",
        "roles": ["integrator"],
        "agent_type": "extract",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase3",
        "layout": "extract",
        "note": "展示：Extraction 与 Rule+LLM 串行；本期仅板块展示",
        "orchestration": "sequence_upstream",
    },
    {
        "feature_id": "F-SVC-003",
        "name": "维修客服多步辅助",
        "purpose": "查车/工单/知识后给出可执行答复",
        "department_id": "service",
        "roles": ["agent", "supervisor"],
        "agent_type": "act",
        "skill_id": "crm_lookup",
        "demo_ready": True,
        "status": "demo",
        "phase": "demo",
        "layout": "crm",
        "input_fields": ["text", "customer_id", "vin"],
        "sample": {
            "text": "客户反馈电机异响，请查车辆与未结工单概况。",
            "customer_id": "CUS-10057",
            "vin": "QS0F65B984410D7B6",
        },
        "placeholder_text": "描述维修咨询…",
        "note": "一期用 crm_lookup 示意主数据多步查询；完整 repair RAG 属 RAG Agent",
    },
    # 用户运营（Planning 主控展示；查数段仍可挂 ReAct）
    {
        "feature_id": "F-UO-001",
        "name": "续费 AI 外呼任务",
        "purpose": "查续费池与意向后组织触达话术",
        "department_id": "user_ops",
        "roles": ["renewal_ops"],
        "agent_type": "plan",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase2",
        "layout": "generic",
        "note": "【Planning 展示】叙事宽于闸门；可跑 Demo 见 F-UO-017 · renewal_plan。上游标签由 Extraction/ReAct 另次写出。",
        "orchestration": "sequence_downstream",
        "flow_ids": ["user_ops_renewal_gate", "story2_outreach_gate"],
        "co_agents": ["extract", "act", "rule_llm"],
    },
    {
        "feature_id": "F-UO-017",
        "name": "Agent 主动触达（投诉闸门）",
        "purpose": "读共享投诉标签后决定是否触达；阻断时给出原因",
        "department_id": "user_ops",
        "roles": ["renewal_ops", "app_cs"],
        "agent_type": "plan",
        "skill_id": "renewal_plan",
        "demo_ready": True,
        "status": "demo",
        "phase": "demo",
        "layout": "generic",
        "input_fields": ["customer_id", "vin", "text"],
        "sample": {
            "text": "评估该用户是否可做续费触达（须读共享投诉标签）。",
            "customer_id": "CUS-10057",
            "vin": "QS0F65B984410D7B6",
        },
        "placeholder_text": "customer_id + vin…",
        "story": "Story2 消费侧（Planning renewal_plan）",
        "note": "【Plan · renewal_plan】另次独立运行读共享层；须先有上游填单/VoC 写出投诉标签。不联跑上游 Agent。",
        "orchestration": "sequence_downstream",
        "flow_ids": ["user_ops_renewal_gate", "story2_outreach_gate"],
        "co_agents": ["extract", "act"],
    },
    {
        "feature_id": "F-UO-019",
        "name": "统一智能客服",
        "purpose": "App 侧多步查主数据再答",
        "department_id": "user_ops",
        "roles": ["app_cs"],
        "agent_type": "act",
        "skill_id": "crm_lookup",
        "demo_ready": True,
        "status": "demo",
        "phase": "demo",
        "layout": "crm",
        "input_fields": ["text", "customer_id", "vin"],
        "sample": {
            "text": "用户问绑车失败，请查客户与车辆状态。",
            "customer_id": "CUS-10057",
            "vin": "QS0F65B984410D7B6",
        },
        "placeholder_text": "App 用户问题…",
        "flow_ids": ["user_ops_renewal_gate"],
    },
    # 订单政策
    {
        "feature_id": "F-OPS-003",
        "name": "智能建单审单",
        "purpose": "查库存→政策→替代→状态建议",
        "department_id": "order_policy",
        "roles": ["order_clerk", "policy_analyst"],
        "agent_type": "act",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase2",
        "layout": "generic",
        "note": "【串行示意】Extraction 抽单 → Rule+LLM 闸门 → ReAct 查数；与 F-POL-RAG（政策问答）并行可选，RAG 不替代本闸门。Skill order_review 待挂。",
        "orchestration": "sequence_upstream",
        "flow_ids": ["order_policy_review", "order_policy_qa"],
    },
    {
        "feature_id": "F-X-004",
        "name": "Agent 建单审单（跨部门线）",
        "purpose": "订单/排产/返利多步推理建议",
        "department_id": "order_policy",
        "roles": ["order_clerk", "policy_analyst"],
        "agent_type": "act",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase2",
        "layout": "generic",
    },
    # 战区
    {
        "feature_id": "F-WZ-001",
        "name": "提货 / 线下问答辅助",
        "purpose": "门店侧查库存+政策给动作清单",
        "department_id": "warzone",
        "roles": ["bd", "manager"],
        "agent_type": "act",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase2",
        "layout": "generic",
    },
    {
        "feature_id": "F-WZ-002",
        "name": "战区建单 / 政策档位辅助",
        "purpose": "战区侧订单与政策 AI 辅助",
        "department_id": "warzone",
        "roles": ["bd", "manager"],
        "agent_type": "act",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase2",
        "layout": "generic",
    },
    # 渠道
    {
        "feature_id": "F-OPS-012",
        "name": "经营健康 / 预警查询",
        "purpose": "查健康指数、预警、巡检切片",
        "department_id": "channel",
        "roles": ["specialist", "manager"],
        "agent_type": "act",
        "skill_id": "channel_ops",
        "demo_ready": True,
        "status": "demo",
        "phase": "demo",
        "layout": "board",
        "input_fields": ["text", "dealer_id"],
        "sample": {
            "text": "请汇总该一代经销商的健康指数、预警与建议动作。",
            "dealer_id": "DLR-3017",
        },
        "placeholder_text": "经销商经营查询…",
        "note": "【并行准备】可与订单侧 F-POL-RAG（policy_kb）同时取口径；看板 Planning 汇合见 F-CH-PLAN（展示）。",
        "orchestration": "parallel_alt",
        "flow_ids": ["channel_ops_board"],
    },
    {
        "feature_id": "F-CH-PLAN",
        "name": "渠道看板汇合（Planning）",
        "purpose": "汇合经营查询与政策口径，生成看板建议",
        "department_id": "channel",
        "roles": ["specialist", "manager"],
        "agent_type": "plan",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase2",
        "layout": "board",
        "note": "【Planning 展示】上游可并行跑 F-OPS-012（ReAct）与 F-POL-RAG；汇合不自动联跑。",
        "orchestration": "sequence_downstream",
        "flow_ids": ["channel_ops_board"],
        "co_agents": ["act", "retrieve"],
    },
    # Rule+LLM（闸门展示）
    {
        "feature_id": "F-OPS-RULE",
        "name": "审单档位闸门",
        "purpose": "规则判定返利/库存档位 + LLM 解释",
        "department_id": "order_policy",
        "roles": ["order_clerk", "policy_analyst"],
        "agent_type": "rule_llm",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase2",
        "layout": "generic",
        "note": "【串行中段 · Rule+LLM】上游 Extraction 抽单 → 本闸门 → 下游 ReAct 查数；与 F-POL-RAG 并行可选。",
        "orchestration": "sequence_downstream",
        "flow_ids": ["order_policy_review"],
    },
    {
        "feature_id": "F-UO-RULE",
        "name": "续费/投诉评分闸门",
        "purpose": "规则+LLM 评定是否允许主动触达",
        "department_id": "user_ops",
        "roles": ["renewal_ops"],
        "agent_type": "rule_llm",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase2",
        "layout": "generic",
        "note": "【串行 · Rule+LLM】读共享投诉标签后评分；完整链路见 Story2 / Planning F-UO-017。",
        "orchestration": "sequence_downstream",
        "flow_ids": ["user_ops_renewal_gate", "story2_outreach_gate"],
    },
    # Vision
    {
        "feature_id": "F-IOT-VISION",
        "name": "产线 / 质检视觉巡检",
        "purpose": "图像理解 → 缺陷标签，供规则汇合告警",
        "department_id": "iot",
        "roles": ["ops", "quality"],
        "agent_type": "vision",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase2",
        "layout": "generic",
        "note": "【并行展示】Vision ∥ Extraction → Rule 汇合；一期不可跑。",
        "orchestration": "parallel_showcase",
        "flow_ids": ["iot_quality_inspect"],
    },
    # 新零售
    {
        "feature_id": "F-RET-001",
        "name": "多平台客服自动回复",
        "purpose": "查订单/库存/活动后回复",
        "department_id": "retail",
        "roles": ["cs", "ops"],
        "agent_type": "act",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase2",
        "layout": "generic",
    },
    {
        "feature_id": "F-RET-002",
        "name": "线上各平台销售客服",
        "purpose": "电商平台销售咨询 AI 承接",
        "department_id": "retail",
        "roles": ["cs"],
        "agent_type": "act",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase2",
        "layout": "generic",
    },
    # 采购
    {
        "feature_id": "F-PUR-001",
        "name": "采购跟单 Bot",
        "purpose": "逾期 PO 催货 + 物流确认",
        "department_id": "procurement",
        "roles": ["buyer", "lead"],
        "agent_type": "act",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase2",
        "layout": "generic",
    },
    {
        "feature_id": "F-PUR-003",
        "name": "智能跟单",
        "purpose": "采购订单跟单自动化",
        "department_id": "procurement",
        "roles": ["buyer"],
        "agent_type": "act",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase2",
        "layout": "generic",
    },
    {
        "feature_id": "F-PUR-004",
        "name": "采购催货提醒",
        "purpose": "多步推理触发采购跟单提醒",
        "department_id": "procurement",
        "roles": ["buyer", "lead"],
        "agent_type": "act",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase2",
        "layout": "generic",
    },
    # 数据
    {
        "feature_id": "F-DAT-003",
        "name": "智能问数",
        "purpose": "澄清指标→查语义层→出数",
        "department_id": "data_lab",
        "roles": ["analyst", "steward"],
        "agent_type": "act",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase2",
        "layout": "generic",
    },
    {
        "feature_id": "F-X-002",
        "name": "BI 语义层 + 智能问数（共用）",
        "purpose": "统一问数与自动报表底座",
        "department_id": "data_lab",
        "roles": ["analyst", "steward"],
        "agent_type": "act",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase2",
        "layout": "generic",
    },
    # 人资
    {
        "feature_id": "F-HR-001",
        "name": "员工 AI 助理 · 制度问答",
        "purpose": "人资制度 / 坐席 SOP RAG 问答",
        "department_id": "hr",
        "roles": ["employee", "hrbp"],
        "agent_type": "retrieve",
        "skill_id": "hr_rules",
        "demo_ready": True,
        "status": "demo",
        "phase": "demo",
        "layout": "rag",
        "input_fields": ["query"],
        "sample": {"query": "坐席质检不能说哪些话？"},
        "placeholder_text": "输入制度/SOP 问题…",
        "note": "【RAG · hr_rules】问答主轴；流程步可用 ReAct",
        "flow_ids": ["hr_policy_qa"],
        "orchestration": "standalone",
        "co_agents": ["act"],
    },
    # IoT
    {
        "feature_id": "F-IOT-003",
        "name": "telemetry 主动服务",
        "purpose": "查告警/里程→建议动作→写产出",
        "department_id": "iot",
        "roles": ["ops", "quality"],
        "agent_type": "act",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase3",
        "layout": "generic",
    },
    # 跨部门共用
    {
        "feature_id": "F-X-CRM",
        "name": "主数据综合查询",
        "purpose": "同一套客户·车·单·工单 ID 查询",
        "department_id": "shared",
        "roles": ["consumer", "integrator"],
        "agent_type": "act",
        "skill_id": "crm_lookup",
        "demo_ready": True,
        "status": "demo",
        "phase": "demo",
        "layout": "crm",
        "input_fields": ["text", "customer_id", "vin", "order_id"],
        "sample": {
            "text": "查询该客户车辆与近期订单概况。",
            "customer_id": "CUS-10057",
            "vin": "QS0F65B984410D7B6",
        },
        "placeholder_text": "主数据查询…",
    },
    {
        "feature_id": "F-X-WRITE",
        "name": "共用信息写入",
        "purpose": "把结果写入共用信息，供其它能力读取",
        "department_id": "shared",
        "roles": ["integrator", "consumer"],
        "agent_type": "act",
        "skill_id": "shared_write",
        "demo_ready": True,
        "status": "demo",
        "phase": "demo",
        "layout": "asset",
        "input_fields": ["text"],
        "sample": {
            "text": "写入一条演示共用信息，供续费触达评估读取使用。",
            "payload": {
                "note": "platform-demo",
                "customer_id": "CUS-10057",
                "tag_id": "TAG-演示",
            },
        },
        "placeholder_text": "描述要写入共用信息的内容…",
    },
    {
        "feature_id": "F-X-READ",
        "name": "共享标签 / 产出读取",
        "purpose": "跨 Skill 消费，阻断错误触达",
        "department_id": "shared",
        "roles": ["consumer", "integrator"],
        "agent_type": "act",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase2",
        "layout": "generic",
        "note": "工具 read_ai_outputs / check_outreach_block 已就绪；独立 Skill 待挂",
    },
    {
        "feature_id": "F-X-CAP",
        "name": "能力目录检索",
        "purpose": "发现已有 Skill，避免重复造 Agent",
        "department_id": "shared",
        "roles": ["integrator"],
        "agent_type": "act",
        "skill_id": None,
        "demo_ready": False,
        "status": "planned",
        "phase": "phase2",
        "layout": "generic",
        "note": "list_capabilities 工具与 /v1/capabilities API 已可用",
    },
    {
        "feature_id": "F-X-CH",
        "name": "渠道经营查询（共用数据源）",
        "purpose": "经营与合规同一数据源",
        "department_id": "shared",
        "roles": ["consumer"],
        "agent_type": "act",
        "skill_id": "channel_ops",
        "demo_ready": True,
        "status": "demo",
        "phase": "demo",
        "layout": "board",
        "input_fields": ["text", "dealer_id"],
        "sample": {
            "text": "从共享视角查看一代健康与预警。",
            "dealer_id": "DLR-3017",
        },
        "placeholder_text": "渠道经营查询…",
    },
]


def list_departments() -> list[dict[str, Any]]:
    out = []
    for d in DEPARTMENTS.values():
        feats = [f for f in FEATURES if f["department_id"] == d["department_id"]]
        out.append(
            {
                "department_id": d["department_id"],
                "name": d["name"],
                "tone_label": d["tone_label"],
                "roles": d["roles"],
                "feature_count": len(feats),
                "demo_count": sum(1 for f in feats if f.get("demo_ready")),
            }
        )
    return out


def get_department(department_id: str) -> dict[str, Any] | None:
    d = DEPARTMENTS.get(department_id)
    if not d:
        return None
    return {
        "department_id": d["department_id"],
        "name": d["name"],
        "tone_label": d["tone_label"],
        "roles": d["roles"],
    }


def list_roles(department_id: str) -> list[dict[str, Any]]:
    d = DEPARTMENTS.get(department_id)
    return list(d["roles"]) if d else []


def _agent_display_name(agent_type: str | None) -> str:
    return display_name(agent_type)


def _feature_phase(f: dict[str, Any]) -> str:
    """归一化阶段：demo | phase2 | phase3。"""
    if f.get("demo_ready") or f.get("status") == "demo":
        return "demo"
    raw = str(f.get("phase") or "").strip().lower()
    if raw in {"demo", "phase1", "一期"}:
        return "demo"
    if raw in {"phase3", "三期", "p3", "3"}:
        return "phase3"
    if raw in {"phase2", "二期", "p2", "2"}:
        return "phase2"
    if canonicalize(f.get("agent_type")) == "vision":
        return "phase3"
    return "phase2"


PHASE_LABELS = {"demo": "Demo", "phase2": "二期", "phase3": "三期"}


def _node_loop(n: dict[str, Any]) -> str | None:
    """flow 节点上的控制环：优先 control_loop，兼容旧 agent_type。"""
    return canonicalize(n.get("control_loop") or n.get("agent_type"))


def _agents_used(f: dict[str, Any], flows: list[dict[str, Any]]) -> list[str]:
    """本功能实际/并列使用的控制环（主类型 + co_agents + 流上并行邻接）；输出规范名。"""
    primary = canonicalize(f.get("agent_type"))
    ordered = list(PLATFORM_LOOPS) + ["rule_llm", "vision"]
    used: list[str] = []

    def add(a: str | None) -> None:
        ca = canonicalize(a)
        if ca and ca not in used:
            used.append(ca)

    add(primary)
    for a in f.get("co_agents") or []:
        add(a)

    skill = f.get("skill_id")
    for fl in flows:
        nodes = fl.get("nodes") or []
        by_id = {}
        for n in nodes:
            nid = n.get("node_id") or n.get("id")
            if nid:
                by_id[nid] = n
        my_ids = set()
        for n in nodes:
            nid = n.get("node_id") or n.get("id")
            if not nid:
                continue
            if skill and n.get("skill_id") == skill:
                my_ids.add(nid)
            elif same_loop(_node_loop(n), primary) and (
                not skill or not n.get("skill_id") or n.get("skill_id") == skill
            ):
                my_ids.add(nid)
        for e in fl.get("edges") or []:
            if e.get("mode") != "parallel":
                continue
            a_from, a_to = e.get("from"), e.get("to")
            if a_from not in my_ids and a_to not in my_ids:
                continue
            for nid in (a_from, a_to):
                add(_node_loop(by_id.get(nid) or {}))

    rest = [a for a in ordered if a in used and a != primary]
    extras = [a for a in used if a != primary and a not in rest]
    return ([primary] if primary else []) + rest + extras


def _public_feature(f: dict[str, Any]) -> dict[str, Any]:
    dept = DEPARTMENTS.get(f["department_id"], {})
    flow_ids = list(f.get("flow_ids") or [])
    flows = []
    for fid in flow_ids:
        fl = get_flow(fid)
        if not fl:
            continue
        modes = {e.get("mode") for e in (fl.get("edges") or [])}
        flows.append(
            {
                "flow_id": fid,
                "name": fl.get("name"),
                "demo_ready": bool(fl.get("demo_ready")),
                "notes": fl.get("notes") or "",
                "has_parallel": "parallel" in modes,
                "has_sequence": "sequence" in modes,
                "parallel_groups": fl.get("parallel_groups") or [],
                "nodes": fl.get("nodes") or [],
                "edges": fl.get("edges") or [],
            }
        )
    orch = f.get("orchestration") or (
        "parallel_showcase" if not f.get("demo_ready") else "standalone"
    )
    agents = _agents_used(f, flows)
    agents_label = "·".join(_agent_display_name(a) for a in agents if a)
    phase = _feature_phase(f)
    agent_type = canonicalize(f["agent_type"]) or f["agent_type"]
    return {
        "feature_id": f["feature_id"],
        "name": f["name"],
        "purpose": f["purpose"],
        "department_id": f["department_id"],
        "department_name": dept.get("name"),
        "tone_label": dept.get("tone_label"),
        "roles": list(f.get("roles") or []),
        "agent_type": agent_type,
        "agents": agents,
        "agents_label": agents_label or _agent_display_name(agent_type),
        "co_agents": [canonicalize(a) or a for a in (f.get("co_agents") or [])],
        "skill_id": f.get("skill_id"),
        "demo_ready": bool(f.get("demo_ready")),
        "status": f.get("status", "planned"),
        "phase": phase,
        "phase_label": PHASE_LABELS.get(phase, "二期"),
        "layout": f.get("layout", "generic"),
        "input_fields": list(f.get("input_fields") or ["text"]),
        "sample": dict(f.get("sample") or {}),
        "placeholder_text": f.get("placeholder_text") or "",
        "story": f.get("story"),
        "note": f.get("note"),
        "flow_ids": flow_ids,
        "flows": flows,
        "orchestration": orch,
    }


def list_features(
    *,
    department_id: str | None = None,
    role_id: str | None = None,
    agent_type: str | None = None,
    demo_only: bool = False,
) -> list[dict[str, Any]]:
    want = canonicalize(agent_type) if agent_type else None
    rows = []
    for f in FEATURES:
        if department_id and f["department_id"] != department_id:
            continue
        if role_id and role_id not in (f.get("roles") or []):
            continue
        if want and not same_loop(f.get("agent_type"), want):
            continue
        if demo_only and not f.get("demo_ready"):
            continue
        rows.append(_public_feature(f))
    return rows


def get_feature(feature_id: str) -> dict[str, Any] | None:
    for f in FEATURES:
        if f["feature_id"] == feature_id:
            return _public_feature(f)
    return None


def list_agent_types() -> list[dict[str, Any]]:
    out = []
    for a in AGENT_TYPES:
        loop_id = a["agent_type"]
        feats = [f for f in FEATURES if same_loop(f.get("agent_type"), loop_id)]
        out.append(
            {
                **a,
                "feature_count": len(feats),
                "demo_count": sum(1 for f in feats if f.get("demo_ready")),
                "features": [_public_feature(f) for f in feats],
            }
        )
    return out


def get_agent_type(agent_type: str) -> dict[str, Any] | None:
    """接受规范名或历史别名（rag/react/extraction/planning）。"""
    want = canonicalize(agent_type)
    for a in list_agent_types():
        if a["agent_type"] == want or agent_type in (a.get("aliases") or []):
            return a
        if a.get("legacy_alias") == agent_type:
            return a
    return None


# ---- 兼容旧 department 视图调用面（供 run API 组装） ----

def public_view_from_feature(f: dict[str, Any]) -> dict[str, Any]:
    """把可跑功能映射为旧 run API 需要的 department 视图字段。"""
    return {
        "department_id": f["department_id"],
        "name": f.get("department_name") or f["department_id"],
        "skill_id": f.get("skill_id"),
        "tone_label": f.get("tone_label"),
        "layout": f.get("layout", "generic"),
        "blurb": f.get("purpose"),
        "input_fields": f.get("input_fields") or ["text"],
        "result_focus": [],
        "placeholder_text": f.get("placeholder_text") or "",
        "sample": f.get("sample") or {},
        "feature_id": f["feature_id"],
        "demo_ready": f.get("demo_ready"),
    }


def resolve_department_for_skill(skill_id: str) -> dict[str, Any] | None:
    for f in FEATURES:
        if f.get("skill_id") == skill_id and f.get("demo_ready"):
            return public_view_from_feature(_public_feature(f))
    return None


# ---------------------------------------------------------------------------
# 部门内编排（department_flows.json · Planning 契约，非运行时）
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def load_department_flows() -> dict[str, Any]:
    """加载机读编排；节点规范化为 V2（skill/placeholder/store_* + control_loop）。"""
    if not _FLOWS_PATH.is_file():
        return {"version": "v2", "flows": []}
    data = json.loads(_FLOWS_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"version": "v2", "flows": []}
    flows = data.get("flows")
    if not isinstance(flows, list):
        data = {**data, "flows": []}
        return data
    data = {**data, "flows": [_normalize_flow(fl) for fl in flows]}
    return data


def _normalize_flow_node(n: dict[str, Any]) -> dict[str, Any]:
    """节点 = 可独立跑的 Skill/功能（或共享层点/占位），非 Agent 管道。"""
    from apps.skill_loops import resolve_skill_control_loop
    from apps.loops import EXTENSION_TYPES

    kind = n.get("kind") or "placeholder"
    skill_id = n.get("skill_id")
    loop = n.get("control_loop") or resolve_skill_control_loop(
        skill_id=skill_id,
        agent_type=n.get("agent_type"),
    )
    loop = canonicalize(loop)
    extension_type = n.get("extension_type")
    if loop in EXTENSION_TYPES:
        extension_type = loop
        loop = EXTENSION_TYPES[loop]["parent_loop"]

    if kind == "agent_type":
        kind = "skill" if skill_id else "placeholder"
    if kind not in {"skill", "placeholder", "store_read", "store_write"}:
        kind = "placeholder"

    out: dict[str, Any] = {
        "node_id": n.get("node_id") or n.get("id"),
        "kind": kind,
        "skill_id": skill_id,
        "control_loop": None if kind in {"store_read", "store_write"} else loop,
        "label": n.get("label") or skill_id or kind,
    }
    if extension_type:
        out["extension_type"] = extension_type
    if n.get("note"):
        out["note"] = n["note"]
    # 兼容旧 UI：附带 agent_type=control_loop（规范名）
    if out.get("control_loop"):
        out["agent_type"] = out["control_loop"]
    return out


def _normalize_flow(fl: dict[str, Any]) -> dict[str, Any]:
    nodes = [_normalize_flow_node(n) for n in (fl.get("nodes") or [])]
    edges = list(fl.get("edges") or [])
    modes = {e.get("mode") for e in edges}
    has_parallel = "parallel" in modes or bool(fl.get("parallel_groups"))
    has_sequence = "sequence" in modes
    return {
        **fl,
        "nodes": nodes,
        "edges": edges,
        "has_parallel": has_parallel,
        "has_sequence": has_sequence,
        # 说明书字段：明确非联跑引擎
        "executable": False,
        "relation_kinds": [
            *(["parallel"] if has_parallel else []),
            *(["shared_dependency"] if has_sequence else []),
        ],
    }


def list_flows(*, demo_ready: bool | None = None) -> list[dict[str, Any]]:
    flows = list(load_department_flows().get("flows") or [])
    if demo_ready is None:
        return flows
    return [f for f in flows if bool(f.get("demo_ready")) is demo_ready]


def get_flow(flow_id: str) -> dict[str, Any] | None:
    for f in list_flows():
        if f.get("flow_id") == flow_id:
            return f
    return None


def get_flows_by_department(department_id: str) -> list[dict[str, Any]]:
    return [f for f in list_flows() if f.get("department_id") == department_id]
