#!/usr/bin/env python3
"""生成 /logic 子页一、二 HTML（部门连线可切换 · Skill 搭建逻辑 · 分期路线图）。"""

from __future__ import annotations

import html
from collections import defaultdict
from pathlib import Path

import yaml

from apps.catalog import DEPARTMENTS, FEATURES

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "apps" / "ui"
V = "20260808-logic4"

LOOP_TECH = {
    "retrieve": "Retrieve",
    "rag": "Retrieve",
    "act": "Act",
    "react": "Act",
    "extract": "Extract",
    "extraction": "Extract",
    "plan": "Plan",
    "planning": "Plan",
    "rule_llm": "Plan（扩展 Rule gate）",
    "vision": "Extract（扩展 Vision）",
}
TOOL_CLASS = {
    "retrieve": "knowledge",
    "rag": "knowledge",
    "act": "read + write_govern",
    "react": "read + write_govern",
    "extract": "write_govern（结构化产出）",
    "extraction": "write_govern（结构化产出）",
    "plan": "write_govern（读共享 + 闸门）",
    "planning": "write_govern（读共享 + 闸门）",
    "rule_llm": "write_govern（规则闸门）",
    "vision": "read / knowledge（感知→标签）",
}

ORDER = [
    "service",
    "user_ops",
    "voc",
    "channel",
    "order_policy",
    "warzone",
    "retail",
    "procurement",
    "iot",
    "data_lab",
    "hr",
    "shared",
]

MODE = {
    "retrieve": ("协作", "坐席/员工发起提问，系统检索后答复，关键承诺转人工"),
    "rag": ("协作", "坐席/员工发起提问，系统检索后答复，关键承诺转人工"),
    "act": ("协作", "业务发起多步查询/填单；写共享前需符合白名单"),
    "react": ("协作", "业务发起多步查询/填单；写共享前需符合白名单"),
    "extract": ("协作", "输入原文，产出 schema 字段；写入共享属审批边界"),
    "extraction": ("协作", "输入原文，产出 schema 字段；写入共享属审批边界"),
    "plan": ("审批", "必须读共享标签后判定放行/阻断，禁止静默触达"),
    "planning": ("审批", "必须读共享标签后判定放行/阻断，禁止静默触达"),
    "rule_llm": ("审批", "规则闸门输出是否通过/档位，供人工确认"),
    "vision": ("上报", "缺陷/状态标签上报质量侧，不直接闭环处罚"),
}


def esc(s: object) -> str:
    return html.escape(str(s or ""))


def biz_name(s: str) -> str:
    s = s or ""
    for a, b in [
        ("Agent 主动触达（投诉闸门）", "主动触达投诉把关"),
        ("Agent 建单审单（跨部门线）", "跨部门建单审单辅助"),
        ("智能填单 · Extraction", "智能填单 · 信息整理"),
        ("智能辅助回答 · RAG", "智能辅助回答"),
        ("政策口径问答 · RAG", "政策口径问答"),
        ("App 智能问答 MVP", "App 智能问答"),
        ("渠道看板汇合（Planning）", "渠道看板汇合"),
        ("telemetry 主动服务", "车况主动服务"),
    ]:
        s = s.replace(a, b)
    return s


def load_skill(sid: str | None) -> dict:
    if not sid:
        return {}
    p = ROOT / "skills" / sid / "skill.yaml"
    if not p.is_file():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def phase_label(f: dict) -> str:
    if f.get("demo_ready"):
        return "一期可试用"
    if f.get("phase") == "phase2":
        return "二期"
    if f.get("phase") == "phase3":
        return "三期"
    return "规划中"


def _tool_groups(tools: list[str]) -> dict[str, list[str]]:
    read_k = (
        "get_customer",
        "get_vehicle",
        "list_vehicles",
        "get_order",
        "list_orders",
        "list_inventory",
        "get_dealer",
        "get_store",
        "get_sku",
        "get_ticket",
        "list_tickets",
        "get_renewal",
        "get_user_behavior",
        "get_dealer_health",
        "list_alerts",
        "list_sales_metrics",
        "list_retail_daily",
        "list_inspections",
        "get_risk",
        "get_policy",
        "simulate_rebate_tier",
        "score_renewal",
        "route_renewal_pool",
    )
    know_k = ("search_kb", "get_kb_document", "list_kb_domains")
    write_k = (
        "write_ai_output",
        "read_ai_outputs",
        "get_ai_output",
        "read_shared_tags",
        "check_outreach_block",
        "extract_ticket_fields",
        "suggest_voc_tags",
        "get_tag",
    )
    g = {"读业务实体": [], "查知识库": [], "整理/写共享/把关": [], "其它": []}
    for t in tools:
        if t in read_k:
            g["读业务实体"].append(t)
        elif t in know_k:
            g["查知识库"].append(t)
        elif t in write_k:
            g["整理/写共享/把关"].append(t)
        elif t != "log_step":
            g["其它"].append(t)
    return {k: v for k, v in g.items() if v}


def tools_biz_text(f: dict, sk: dict, at: str) -> str:
    tools = sk.get("allowed_tools") or []
    if isinstance(tools, dict):
        tools = list(tools.keys())
    tclass = TOOL_CLASS.get(at, "")
    if tools:
        parts = []
        for label, arr in _tool_groups(tools).items():
            # map tool ids to short biz labels
            nice = {
                "get_customer": "客户",
                "get_vehicle": "车辆",
                "list_vehicles": "车辆列表",
                "get_order": "订单",
                "list_orders": "订单列表",
                "list_inventory": "库存",
                "get_dealer": "经销商",
                "get_store": "门店",
                "get_sku": "商品",
                "get_ticket": "工单",
                "list_tickets": "工单列表",
                "search_kb": "检索知识块",
                "get_kb_document": "取全文",
                "list_kb_domains": "知识域列表",
                "write_ai_output": "写入共用产出",
                "read_ai_outputs": "读取共用产出",
                "read_shared_tags": "读共用标签",
                "check_outreach_block": "触达阻断检查",
                "extract_ticket_fields": "抽工单字段",
                "suggest_voc_tags": "建议主题标签",
                "get_tag": "标签字典",
                "get_renewal": "续费档案",
                "get_user_behavior": "行为数据",
                "score_renewal": "续费评分",
                "route_renewal_pool": "续费池分层",
                "get_dealer_health": "经销商健康",
                "list_alerts": "预警",
                "list_inspections": "巡检",
                "get_policy": "政策切片",
            }
            shown = "、".join(nice.get(x, x) for x in arr[:8])
            parts.append(f"{label}（{shown}）")
        return f"工具类 {tclass}。本功能实际会用到：{'；'.join(parts)}。"
    if at in {"retrieve", "rag"}:
        return "工具类 knowledge。检索维修/政策/制度等知识块，再交给生成模型组织答复（需带引用）。"
    if at in {"extract", "extraction"}:
        return "工具类 write_govern（结构化）。按 schema 从原文抽字段/标签；需要沉淀时再写入共用产出。"
    if at in {"plan", "planning", "rule_llm"}:
        return "工具类 write_govern。先读共用标签/产出，再做放行或档位判定；不直接外呼。"
    if at == "vision":
        return "感知输入（影像/台架）→ 识别缺陷标签并上报；工具边界以只读/标注为主。"
    return f"工具类 {tclass or '待定'}。上线前按「读哪些实体 / 是否写共享 / 是否查知识」补齐工具清单。"


def skill_build_logic_html(f: dict, sk: dict) -> str:
    """业务+技术都能读的搭建逻辑：实体 → 处理 → 模型 → 工具 → 产出。"""
    sid = f.get("skill_id")
    at = f.get("agent_type") or ""
    loop = LOOP_TECH.get(at, at)
    purpose = f.get("purpose") or "完成本功能目标"
    name = biz_name(f.get("name") or "")

    # presets by known skill
    presets: dict[str, dict[str, str]] = {
        "fill_ticket": {
            "entity": "客户、车辆、既有工单（主数据）；必要时标签字典",
            "process": "核对身份与未结工单 → 从对话原文抽工单字段并建议主题标签 → 组装工单草案",
            "model": "多步办事模型（Act）：决定查什么、何时写入；字段抽取可用规则工具辅助",
            "tools": "读客户/车辆/工单；抽字段与打标；写入共用产出供续费等读取",
            "out": "工单草案 + 投诉类标签进入共用层；一次运行只完成填单，不自动触达",
        },
        "ticket_fields": {
            "entity": "客服/用户原文；客户与车辆 ID（若提供）",
            "process": "按工单草案 schema 抽取类型、摘要、标签、情感、是否投诉等字段并校验齐全",
            "model": "信息整理模型（Extract）：偏结构化抽取与校验，不做多步查库脑回路",
            "tools": "以 schema 校验为主；需要沉淀时再写入共用产出",
            "out": "结构化工单草案，可与填单功能并行，供坐席确认或下游读取",
        },
        "repair_kb": {
            "entity": "维修知识库文档块（续航/异响/绑车/充电等），一般不强制查车辆主数据",
            "process": "按问题检索相关知识片段 → 把片段塞进提示 → 生成分步建议并标注引用来源",
            "model": "知识问答模型（Retrieve）：检索 + 生成，要求可引用；无命中要说明未覆盖",
            "tools": "检索知识块、取文档、列出知识域",
            "out": "带引用的排查/处理建议；可复用于 App 问答等场景",
        },
        "policy_kb": {
            "entity": "政策知识库（三包/返利/触达红线/门店规范等）",
            "process": "检索政策条款片段 → 生成口径说明并引用条款",
            "model": "知识问答模型（Retrieve），禁止编造未检索到的条款",
            "tools": "检索知识块、取文档、列出知识域",
            "out": "可核对来源的政策口径答复",
        },
        "hr_rules": {
            "entity": "人资制度与坐席质检 SOP 知识库",
            "process": "检索制度/SOP 要点 → 生成答复；涉及个案处分引导转人工",
            "model": "知识问答模型（Retrieve）",
            "tools": "检索知识块、取文档、列出知识域",
            "out": "制度/质检要点答复 + 引用",
        },
        "crm_lookup": {
            "entity": "客户、车辆、订单、库存、经销商/门店/商品等主数据",
            "process": "按 ID 查询相关实体 → 汇总成简短结论（控制在少数要点内）",
            "model": "多步办事模型（Act）：编排查询顺序，少废话多事实",
            "tools": "读客户/车辆/订单/库存等查询工具",
            "out": "主数据核对结论，供客服或续费前查档",
        },
        "channel_ops": {
            "entity": "经销商健康、预警、巡检、销量/零售日报、政策相关切片",
            "process": "按经营问题拉取健康/预警/巡检等数据 → 整理成看板式简报",
            "model": "多步办事模型（Act）",
            "tools": "经销商健康、预警、巡检、销量与政策查询类工具",
            "out": "经营简报（数字 + 异常 + 建议下一步）",
        },
        "renewal_plan": {
            "entity": "共用投诉/风险标签、共用产出；续费档案与行为数据（放行时）",
            "process": "先读共用标签做触达阻断检查 → 若阻断则说明原因；若放行再查续费池并给出短计划",
            "model": "计划把关模型（Plan）：先规则/工具闸门，再组织计划说明",
            "tools": "读共用标签/产出、触达阻断检查；放行后可读续费评分与分层",
            "out": "允许或暂缓触达 + 原因；放行时附续费分层与触达阶梯（仍不自动外呼）",
        },
        "shared_write": {
            "entity": "业务传入的结构化结果（payload）",
            "process": "校验可写范围 → 写入共用产出并返回编号，供其他功能另开运行读取",
            "model": "多步办事模型（Act）中的写共享步骤，逻辑以工具调用与权限为主",
            "tools": "写入/读取共用产出",
            "out": "共用产出 ID，跨部门可消费",
        },
        "voc_entities": {
            "entity": "客户原声文本",
            "process": "抽取主题、情感、风险等实体并对照标签字典 → 需要时写入共用层",
            "model": "信息整理模型（Extract）",
            "tools": "结构化抽取与校验；写共享时走共用写入",
            "out": "原声结构化结果，供服务/续费等读取",
        },
    }

    if sid and sid in presets:
        p = presets[sid]
    elif at in {"retrieve", "rag"}:
        p = {
            "entity": "对应知识域文档（按功能指定维修/政策/制度等）",
            "process": "检索相关片段 → 组织答复并保留引用",
            "model": "知识问答模型（Retrieve）",
            "tools": "知识检索类工具",
            "out": purpose,
        }
    elif at in {"extract", "extraction"}:
        p = {
            "entity": "业务原文或单据文本",
            "process": "按约定字段表抽取并校验完整性",
            "model": "信息整理模型（Extract）",
            "tools": "结构化抽取；必要时写入共用产出",
            "out": purpose,
        }
    elif at in {"plan", "planning", "rule_llm"}:
        p = {
            "entity": "共用标签/产出 + 本业务相关档案",
            "process": "读取共享信号 → 规则或闸门判定 → 输出放行/暂缓与原因",
            "model": "计划把关模型（Plan）",
            "tools": "读共享、闸门检查、必要的业务查询",
            "out": purpose,
        }
    elif at == "vision":
        p = {
            "entity": "产线影像/台架检测数据",
            "process": "识别缺陷或状态 → 生成标签并上报质量侧",
            "model": "影像识别扩展（挂在 Extract 感知侧）",
            "tools": "感知输入与标注输出（分期实现）",
            "out": purpose,
        }
    else:
        p = {
            "entity": "本功能相关的客户/订单/渠道等主数据（按目标裁剪）",
            "process": "多步查询与整理 → 形成可执行结论；写共享须声明谁可读取",
            "model": "多步办事模型（Act）",
            "tools": "读主数据；按需写共用或打标",
            "out": purpose,
        }

    title = f"「{name}」能力包搭建逻辑"
    if sid:
        title += f"（{sid} · {loop}）"
    else:
        title += f"（待挂载 · 建议 {loop}）"

    return f"""<div class="skill-logic">
              <p class="skill-logic-title">{esc(title)}</p>
              <ol>
                <li><b>调用哪些业务数据/知识：</b>{esc(p['entity'])}</li>
                <li><b>做什么样的处理：</b>{esc(p['process'])}</li>
                <li><b>交给什么样的模型/办事方式：</b>{esc(p['model'])}</li>
                <li><b>调用哪些工具能力：</b>{esc(p['tools'])}</li>
                <li><b>产出什么、如何被下游使用：</b>{esc(p['out'])}</li>
              </ol>
            </div>"""


def nav(active: int) -> str:
    flags = [""] * 4
    flags[active] = 'class="active" '
    return f"""      <nav class="logic-subnav" aria-label="逻辑子页">
        <a {flags[0]}href="/logic">总览</a>
        <a {flags[1]}href="/logic/architecture">子页一 · 公司架构拆解</a>
        <a {flags[2]}href="/logic/solution">子页二 · AI 方案设计</a>
        <a {flags[3]}href="/logic/risk">子页三 · 风险管控</a>
      </nav>"""


def shell(title: str, body: str, scripts: str = "") -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{esc(title)}</title>
    <link rel="stylesheet" href="/static/styles.css?v={V}" />
    <link rel="stylesheet" href="/static/logic.css?v={V}" />
  </head>
  <body class="page-logic">
    <nav class="mode-switch" aria-label="界面切换">
      <a href="/business">业务主管</a>
      <a href="/ops">IT 运维</a>
      <a class="active" href="/logic" aria-current="page">逻辑讲解</a>
    </nav>
    <div class="shell shell-wide shell-logic">
{body}
    </div>
{scripts}
  </body>
</html>
"""


def build_dept_flow_svg(by: dict) -> str:
    pos = {
        "warzone": (90, 50),
        "channel": (310, 50),
        "order_policy": (530, 50),
        "retail": (750, 50),
        "data_lab": (970, 50),
        "service": (200, 210),
        "voc": (420, 210),
        "user_ops": (640, 210),
        "hr": (860, 210),
        "procurement": (200, 380),
        "iot": (450, 380),
        "shared": (760, 380),
    }
    edges = [
        ("warzone", "channel", "line-a"),
        ("channel", "order_policy", "line-a"),
        ("order_policy", "retail", "line-a"),
        ("retail", "data_lab", "line-a"),
        ("channel", "shared", "line-a"),
        ("order_policy", "shared", "line-a"),
        ("service", "shared", "line-b"),
        ("voc", "shared", "line-b"),
        ("shared", "user_ops", "line-b"),
        ("user_ops", "service", "line-b"),
        ("service", "voc", "line-c"),
        ("service", "hr", "line-c"),
        ("hr", "shared", "line-c"),
        ("procurement", "iot", "line-d"),
        ("iot", "data_lab", "line-d"),
        ("iot", "shared", "line-d"),
        ("procurement", "shared", "line-d"),
    ]

    # which nodes belong to which line (for highlight)
    line_nodes = {
        "a": {"warzone", "channel", "order_policy", "retail", "data_lab", "shared"},
        "b": {"service", "voc", "user_ops", "shared"},
        "c": {"service", "voc", "hr", "shared"},
        "d": {"procurement", "iot", "data_lab", "shared"},
    }

    edge_svg = []
    for a, b, cls in edges:
        x1, y1 = pos[a]
        x2, y2 = pos[b]
        line = cls.replace("line-", "")
        # slight per-line curve offset to reduce overlap when all shown
        bend = {"a": -28, "b": -8, "c": 12, "d": 28}.get(line, 0)
        mx, my = (x1 + x2) / 2 + bend * 0.3, (y1 + y2) / 2 + bend
        edge_svg.append(
            f'<path class="flow-edge {cls}" data-line="{line}" '
            f'd="M{x1},{y1} Q{mx},{my} {x2},{y2}" fill="none"/>'
        )

    node_svg = []
    for did, (x, y) in pos.items():
        dname = biz_name(DEPARTMENTS.get(did, {}).get("name", did))
        short = dname.replace("运营管理 · ", "").replace(" / ", "/")
        n = len(by.get(did, []))
        lines = "".join(k for k, s in line_nodes.items() if did in s)
        node_svg.append(
            f'''<g class="flow-node" data-lines="{lines}" transform="translate({x},{y})">
  <rect x="-74" y="-30" width="148" height="60" rx="10"/>
  <text class="flow-node-title" y="-2" text-anchor="middle">{esc(short)}</text>
  <text class="flow-node-meta" y="18" text-anchor="middle">{n} 项功能</text>
</g>'''
        )

    return f"""
        <div class="dept-flow-wrap" id="dept-flow">
          <div class="line-dot-bar" role="tablist" aria-label="切换业务主线连线">
            <button type="button" class="line-dot active" data-line="a" aria-pressed="true">
              <i class="dot a"></i><span>主线 A · 商城/渠道销售</span>
            </button>
            <button type="button" class="line-dot" data-line="b" aria-pressed="false">
              <i class="dot b"></i><span>主线 B · App 续费</span>
            </button>
            <button type="button" class="line-dot" data-line="c" aria-pressed="false">
              <i class="dot c"></i><span>主线 C · 售后服务</span>
            </button>
            <button type="button" class="line-dot" data-line="d" aria-pressed="false">
              <i class="dot d"></i><span>主线 D · 生产制造</span>
            </button>
            <button type="button" class="line-dot line-dot-all" data-line="all" aria-pressed="false">
              <i class="dot all"></i><span>全部（淡显）</span>
            </button>
          </div>
          <svg class="dept-flow-svg" viewBox="0 0 1100 460" role="img" aria-label="部门业务连线流程图">
            {''.join(edge_svg)}
            {''.join(node_svg)}
          </svg>
          <p class="card-note" style="margin:8px 0 0">
            点击上方色点只显示该业务主线的连线，避免重叠。节点为部门；跨部门共用层承接标签与产出读写。
          </p>
        </div>"""


def build_architecture(by: dict) -> str:
    pain = {
        "service": "填单慢、知识分散、投诉难沉淀到下游",
        "user_ops": "续费触达与投诉风险未打通",
        "voc": "客户原声难结构化、难被其他部门使用",
        "channel": "经营数据分散、异常发现偏晚",
        "order_policy": "政策口径不一、审单依赖经验",
        "warzone": "一线答疑与建单缺少统一辅助",
        "retail": "多平台客服话术与查询重复劳动",
        "procurement": "跟单催货依赖人工盯梢",
        "iot": "质检与车况告警依赖专人经验",
        "data_lab": "问数门槛高、口径不统一",
        "hr": "制度问答占用人资重复解答",
        "shared": "跨部门缺少统一写入与读取约定",
    }
    kpi = {
        "service": "首次解决率 · 填单时长 · 投诉闭环时效",
        "user_ops": "续费率 · 不当触达次数 · 放行准确率",
        "voc": "标签覆盖率 · 原声到可用信息时延",
        "channel": "异常门店覆盖 · 经营问数自助占比",
        "order_policy": "政策答疑时效 · 审单一致性",
        "warzone": "一线响应时效 · 建单一次通过率",
        "retail": "自动回复占比 · 转人工率",
        "procurement": "逾期 PO 处理时效",
        "iot": "一次交检合格率 · 告警响应时长",
        "data_lab": "问数自助率 · 口径争议次数",
        "hr": "制度自助解答占比",
        "shared": "共用信息被消费次数 · 重复建设项",
    }
    roi = {
        "service": "单均处理时长下降；投诉信息被续费等场景复用",
        "user_ops": "不当外呼趋近于零；放行名单转化可对比",
        "voc": "原声利用次数上升；主题发现周期缩短",
        "channel": "异常更早发现；报表拼数工时下降",
        "order_policy": "答疑自助占比提升；审单返工下降",
        "warzone": "一线等待时间下降",
        "retail": "人工重复答复下降",
        "procurement": "催货及时率提升",
        "iot": "漏检与停机损失下降（分期测定）",
        "data_lab": "取数等待缩短；口径统一",
        "hr": "重复咨询量下降",
        "shared": "跨部门对接成本下降；排障可追溯",
    }

    rows = []
    for did in ORDER:
        feats = by.get(did) or []
        if not feats:
            continue
        dname = biz_name(DEPARTMENTS.get(did, {}).get("name", did))
        for i, f in enumerate(feats):
            name = biz_name(f["name"])
            purpose = f.get("purpose") or ""
            for a, b in [
                ("读共享投诉标签后决定是否触达；阻断时给出原因", "读取共用投诉信息后决定是否允许触达；暂缓时说明原因"),
                ("跨 Skill 消费，阻断错误触达", "供其他功能读取共用信息，用于阻止不当触达"),
                ("发现已有 Skill，避免重复造 Agent", "查找公司已有能力，避免各部门重复建设"),
            ]:
                purpose = purpose.replace(a, b)
            dept_td = (
                f'<td class="dept-merge" rowspan="{len(feats)}">{esc(dname)}</td>' if i == 0 else ""
            )
            rows.append(
                f"""              <tr>
                {dept_td}
                <td><code>{esc(f['feature_id'])}</code> {esc(name)}</td>
                <td>{esc(pain.get(did, ''))}</td>
                <td>{esc(name)}：{esc(purpose)}</td>
                <td>{esc(phase_label(f))}</td>
                <td>{esc(kpi.get(did, ''))}</td>
                <td>{esc(roi.get(did, ''))}</td>
              </tr>"""
            )

    body = f"""
      <header class="topbar">
        <div class="topbar-brand">
          <div class="eyebrow">Qingshu Mobility</div>
          <h1>子页一 · 公司架构拆解</h1>
        </div>
        <div class="topbar-right">
          <div class="topbar-meta">部门连线流程 · 业务主线 · 规划功能与 KPI<br />战略：效率优化与业务拓展</div>
        </div>
      </header>
{nav(1)}
      <div class="logic-hero">
        <p class="logic-lead">
          在五年战略「引入 AI，转型内部架构与产品线」之下：先用<strong>部门节点 + 分色业务连线</strong>看清协作关系，
          再沿四条业务主线展开产出入与 AI 将承担的功能，最后用规划功能清单对齐部门 KPI。
        </p>
      </div>

      <section class="logic-section">
        <h2>部门流程图（节点 = 部门 · 连线 = 业务主线）</h2>
        <p class="sec-note">共规划 <strong>{len(FEATURES)}</strong> 项功能。默认只显示主线 A；点选色点切换连线。</p>
        {build_dept_flow_svg(by)}
      </section>

      <section class="logic-section">
        <h2>四条业务主线 · 流程与各部门将获 AI 功能</h2>
        <p class="sec-note">绿色文字表示 AI 将为相关部门承担的功能（业务语言）。</p>
        <div class="logic-legend">
          <span>步骤 = 业务环节</span>
          <span class="lg-io">棕色 = 投入 / 产出</span>
          <span class="lg-ai">绿色 = AI 将承担的功能</span>
        </div>
        <div class="flow-grid">
          <article class="flow-card">
            <h3>主线 A · 商城 / 渠道销售</h3>
            <p class="flow-meta">战区 → 渠道 → 订单政策 → 新零售 / 数据研究院（见图连线青色）</p>
            <ol class="flow-steps">
              <li class="flow-step"><div class="n">1</div><div class="body"><strong>开店与提货推进</strong><div class="io">投入：战区目标、门店档案 · 产出：开店进度、提货计划</div></div></li>
              <li class="flow-step ai-hot"><div class="n">2</div><div class="body"><strong>渠道经营与异常发现</strong><div class="io">投入：销量、库存、巡检 · 产出：健康情况、异常清单</div><div class="ai-need">AI 功能：经营健康查询、异常提醒、渠道相关问数</div></div></li>
              <li class="flow-step ai-hot"><div class="n">3</div><div class="body"><strong>政策答疑与审单辅助</strong><div class="io">投入：政策文件、订单 · 产出：口径说明、审单建议</div><div class="ai-need">AI 功能：政策口径问答、销售政策整理、建单审单辅助、档位把关</div></div></li>
              <li class="flow-step"><div class="n">4</div><div class="body"><strong>经营结果回流</strong><div class="io">投入：战区汇总 · 产出：经营复盘输入</div></div></li>
            </ol>
          </article>
          <article class="flow-card">
            <h3>主线 B · App 续费</h3>
            <p class="flow-meta">服务 / 用研 → 共用层 → 用户运营（见图连线琥珀色）</p>
            <ol class="flow-steps">
              <li class="flow-step"><div class="n">1</div><div class="body"><strong>续费客户分层</strong><div class="io">投入：到期日、活跃度 · 产出：分层名单</div></div></li>
              <li class="flow-step ai-hot"><div class="n">2</div><div class="body"><strong>触达前合规判断</strong><div class="io">投入：客户、车辆、共用投诉信息 · 产出：允许或暂缓触达</div><div class="ai-need">AI 功能：主动触达投诉把关；续费/投诉评分把关</div></div></li>
              <li class="flow-step ai-hot"><div class="n">3</div><div class="body"><strong>组织触达任务</strong><div class="io">投入：放行名单 · 产出：外呼或推送任务</div><div class="ai-need">AI 功能：续费外呼任务组织（二期）；统一智能客服查询辅助</div></div></li>
              <li class="flow-step"><div class="n">4</div><div class="body"><strong>续费结果回流</strong><div class="io">投入：成交/拒访 · 产出：漏斗复盘</div></div></li>
            </ol>
          </article>
          <article class="flow-card">
            <h3>主线 C · 售后服务</h3>
            <p class="flow-meta">服务 ↔ 用研 / 人资 ↔ 共用层（见图连线绿色）</p>
            <ol class="flow-steps">
              <li class="flow-step ai-hot"><div class="n">1</div><div class="body"><strong>进线接待与知识答复</strong><div class="io">投入：用户问题 · 产出：可核对来源的答复</div><div class="ai-need">AI 功能：维修知识问答、智能辅助回答、App 侧同类问答</div></div></li>
              <li class="flow-step ai-hot"><div class="n">2</div><div class="body"><strong>工单信息整理与填单</strong><div class="io">投入：沟通原文 · 产出：工单草案、情绪与主题</div><div class="ai-need">AI 功能：智能填单、工单信息整理、维修多步查询辅助</div></div></li>
              <li class="flow-step ai-hot"><div class="n">3</div><div class="body"><strong>投诉与主题沉淀</strong><div class="io">投入：工单草案、客户原声 · 产出：可供其他部门使用的共用信息</div><div class="ai-need">AI 功能：客户原声整理、故障主题聚类、共用信息写入</div></div></li>
              <li class="flow-step ai-hot"><div class="n">4</div><div class="body"><strong>结案与质检复盘</strong><div class="io">投入：服务过程材料 · 产出：质检结论</div><div class="ai-need">AI 功能：智能质检（三期）；制度问答支撑人资侧辅导</div></div></li>
            </ol>
          </article>
          <article class="flow-card">
            <h3>主线 D · 生产制造</h3>
            <p class="flow-meta">采购 → IoT → 数据研究院 / 共用层（见图连线紫色）</p>
            <ol class="flow-steps">
              <li class="flow-step ai-hot"><div class="n">1</div><div class="body"><strong>排产与采购跟单</strong><div class="io">投入：订单与交期 · 产出：跟单状态、催货提醒</div><div class="ai-need">AI 功能：采购跟单、智能跟单、催货提醒</div></div></li>
              <li class="flow-step ai-hot"><div class="n">2</div><div class="body"><strong>产线质检与追溯</strong><div class="io">投入：台架/画面 · 产出：合格判定、问题记录</div><div class="ai-need">AI 功能：产线/质检视觉巡检（二期）</div></div></li>
              <li class="flow-step ai-hot"><div class="n">3</div><div class="body"><strong>车况与主动服务</strong><div class="io">投入：车况数据 · 产出：服务提醒</div><div class="ai-need">AI 功能：车况主动服务（三期）</div></div></li>
              <li class="flow-step ai-hot"><div class="n">4</div><div class="body"><strong>经营与质量问数</strong><div class="io">投入：指标语义 · 产出：经营问答结论</div><div class="ai-need">AI 功能：智能问数、语义层问数（二期）</div></div></li>
            </ol>
          </article>
        </div>
      </section>

      <section class="logic-section">
        <h2>公司五年战略基座</h2>
        <div class="strategy-strip">
          <div class="strategy-cell"><h4>战略方向</h4><p>引入 AI，对公司内部架构与产品线进行转型；形成可复用、可管理的企业能力。</p></div>
          <div class="strategy-cell"><h4>引入模式</h4><p><strong>效率优化与业务拓展</strong>：缩短处理时长、提升转化与体验；不以减少人力作为目标表述。</p></div>
          <div class="strategy-cell"><h4>对齐方式</h4><p>数字化基座 + 部门规划功能 + 部门 KPI，共同服务公司战略。</p></div>
        </div>
      </section>

      <section class="logic-section">
        <h2>部门功能需求（与规划清单一致 · 共 {len(FEATURES)} 项）</h2>
        <p class="sec-note">相同部门单元格已合并居中；逐条对应规划功能。</p>
        <div class="kpi-table-wrap">
          <table class="kpi-table">
            <thead>
              <tr>
                <th>部门</th>
                <th>规划功能</th>
                <th>当前痛点</th>
                <th>未来功能说明</th>
                <th>阶段</th>
                <th>部门 KPI 关注</th>
                <th>价值测定方向</th>
              </tr>
            </thead>
            <tbody>
{chr(10).join(rows)}
            </tbody>
          </table>
        </div>
      </section>

      <div class="logic-footer-nav">
        <a href="/logic">← 总览</a>
        <a href="/logic/solution">进入子页二 →</a>
      </div>
"""
    scripts = f'    <script src="/static/logic-flow.js?v={V}"></script>\n'
    return shell("青枢出行 · 子页一 · 公司架构拆解", body, scripts=scripts)


def build_solution(by: dict) -> str:
    dept_blocks = []
    for did in ORDER:
        feats = by.get(did) or []
        if not feats:
            continue
        dname = biz_name(DEPARTMENTS.get(did, {}).get("name", did))
        feat_html = []
        for f in feats:
            at = f.get("agent_type") or ""
            loop = LOOP_TECH.get(at, at)
            sk = load_skill(f.get("skill_id"))
            tools_txt = tools_biz_text(f, sk, at)
            mode, mode_desc = MODE.get(at, ("协作", "业务发起，AI 协助"))
            logic_html = skill_build_logic_html(f, sk)
            name = biz_name(f["name"])
            feat_html.append(
                f"""            <article class="feat-judge">
              <div class="feat-judge-title">
                <strong>{esc(name)}</strong>
                <code>{esc(f['feature_id'])}</code>
                <span class="pill pill-ghost">{esc(phase_label(f))}</span>
              </div>
              <p class="feat-purpose">{esc(f.get('purpose') or '')}</p>
              <div class="feat-grid tech-grid">
                <div><h5>Control Loop</h5><p><b>{esc(loop)}</b></p></div>
                <div><h5>Tools（工具边界）</h5><p>{esc(tools_txt)}</p></div>
                <div><h5>相处模式</h5><p><b>{esc(mode)}</b> — {esc(mode_desc)}</p></div>
                <div class="feat-span"><h5>Skill 搭建逻辑</h5>{logic_html}</div>
              </div>
            </article>"""
            )

        routes = {
            "service": "进线先用 Retrieve 查维修知识 → 可并行：Extract 整理工单字段 ∥ Act 核对客户/车辆并写共用产出 → 用户运营另开 Plan 读取投诉标签做触达把关。",
            "user_ops": "App 侧 Retrieve/Act 答疑与查档 → 另开 Plan 读共用投诉标签做放行/暂缓；真实外呼任务放二期，且不与上游自动联跑。",
            "voc": "Extract 把客户原声整理成主题/情感等结构 → 写入共用层 → 服务与续费另行读取。",
            "channel": "Act 拉取经营健康/预警等出简报 → 二期看板汇合后由人工确认再发布。",
            "order_policy": "Retrieve 答政策口径 ∥ Extract 整理政策要点 → Act/Rule 做审单或档位把关。",
            "shared": "承接写入/读取共用产出与标签；提供能力目录查询，避免各部门重复建设同类能力。",
        }

        assets = {
            "service": "写出：工单草案、投诉/风险类标签、情感等；明确允许用户运营续费把关读取。",
            "user_ops": "读取：共用投诉标签与产出；产出：是否允许触达、原因、续费短计划。",
            "voc": "写出：原声结构化结果（主题、实体、情感等）。",
            "channel": "读取：经销商健康/预警等；产出：经营简报要点。",
            "order_policy": "知识域：政策；产出：口径答复与档位建议。",
            "shared": "平台资产：标签字典、共用 AI 产出、能力目录、统一工具注册。",
        }

        dept_blocks.append(
            f"""
      <section class="logic-section dept-card">
        <h2>{esc(dname)} <span class="dept-count-inline">{len(feats)} 项功能</span></h2>
        <p class="sec-note">逐功能保留 Control Loop；Skill 用「数据 → 处理 → 模型 → 工具 → 产出」说明搭建逻辑，业务主管与技术同事都能跟读。</p>
        <div class="feat-judge-list">
{chr(10).join(feat_html)}
        </div>
        <h3 class="subhead">本部门 AI 业务顺序</h3>
        <div class="asset-card" style="max-width:100%"><p style="margin:0">{esc(routes.get(did, '各功能分别试跑；跨功能只经共用层另开运行。'))}</p></div>
        <h3 class="subhead">共用数字资产（本部门相关）</h3>
        <div class="asset-card" style="max-width:100%"><p style="margin:0">{esc(assets.get(did, '按功能声明谁写入、谁可读取、用哪些标签。'))}</p></div>
      </section>"""
        )

    def kpi_for_dept(did: str, name: str = "") -> str:
        if did == "user_ops":
            return "不当触达事故 = 0（闸门扩展）"
        if did == "voc":
            return "标签覆盖率↑"
        if did == "procurement":
            return "催货及时率↑"
        if did == "data_lab":
            return "问数自助率↑"
        if did == "retail":
            return "自动回复占比↑"
        if did == "iot" or "质检" in name:
            return "漏检率基线建立 / 漏检率↓"
        if did == "shared":
            return "共享读取稳定、可审计"
        if did in {"channel", "order_policy", "warzone", "hr"}:
            return "自助答疑占比↑ · 异常发现提前"
        return "可单跑验收 · 业务闭环时效↑"

    p1_feats = [f for f in FEATURES if f.get("demo_ready")]
    p2_feats = [f for f in FEATURES if f.get("phase") == "phase2" and not f.get("demo_ready")]
    p3_feats = [f for f in FEATURES if f.get("phase") == "phase3" and not f.get("demo_ready")]

    def feat_chips(feats: list) -> str:
        chips = []
        for f in feats:
            did = f["department_id"]
            dshort = biz_name(DEPARTMENTS.get(did, {}).get("name", did))
            dshort = dshort.replace("运营管理 · ", "").replace(" / ", "/")
            chips.append(
                f'<div class="phase-feat">'
                f'<strong>{esc(biz_name(f["name"]))}</strong>'
                f'<span class="phase-feat-dept">{esc(dshort)}</span>'
                f'<span class="phase-feat-kpi">{esc(kpi_for_dept(did, biz_name(f["name"])))}</span>'
                f"</div>"
            )
        return "".join(chips) if chips else '<p class="card-note">按 catalog 分期挂载</p>'

    body = f"""
      <header class="topbar">
        <div class="topbar-brand">
          <div class="eyebrow">Qingshu Mobility · Solution Logic</div>
          <h1>子页二 · AI 方案设计逻辑</h1>
        </div>
        <div class="topbar-right">
          <div class="topbar-meta">Control Loop 保留 · Skill 搭建逻辑<br />一二三期路线与当期 KPI</div>
        </div>
      </header>
{nav(2)}
      <div class="logic-hero">
        <p class="logic-lead">
          以<strong>部门为大卡片</strong>，对每个功能给出 <b>Control Loop</b>、工具边界、相处模式，以及
          <b>Skill 搭建逻辑</b>：调用哪些业务数据/知识 → 做何种处理 → 交给何种模型/办事方式 → 用哪些工具 → 产出如何被下游使用。
        </p>
      </div>
{''.join(dept_blocks)}

      <section class="logic-section" style="border:none;padding:0;background:transparent;box-shadow:none">
        <div class="innov-float">
          <div class="innov-badge">我的创新点</div>
          <h3>平台统一：4 Control Loops + 3 类工具 + 共用存储</h3>
          <p class="innov-claim">
            办事环：Retrieve / Act / Extract / Plan；工具类：读主数据 / 查知识 / 写共享与把关；
            跨部门只经共用产出与标签字典协作。价值：防孤岛、统一观测、按环控成本、写共享可审计。
          </p>
        </div>
      </section>

      <section class="logic-section phase-roadmap-sec">
        <h2>一期 / 二期 / 三期 · 建设路线</h2>
        <p class="sec-note">一期打通底座与跨部门互通；二、三期按功能扩展，并给出可测 KPI。</p>
        <div class="phase-roadmap">
          <article class="phase-panel phase1">
            <header class="phase-panel-head">
              <span class="phase-num">01</span>
              <div>
                <h4>一期 · 底座互通</h4>
                <p>必达 · 可试用</p>
              </div>
            </header>
            <div class="phase-block">
              <h5>平台要交付什么</h5>
              <div class="phase-chips">
                <span>4 个 Control Loop 可运行</span>
                <span>统一工具注册（读 / 知识 / 写共享）</span>
                <span>唯一取数通道</span>
                <span>共用层：标签字典 + AI 产出</span>
              </div>
            </div>
            <div class="phase-block">
              <h5>跨部门怎么验收</h5>
              <p>服务写入的投诉标签，用户运营 Plan 能读到并正确阻断；同一工具可被多部门能力包复用。</p>
            </div>
            <div class="phase-block">
              <h5>本期可试用功能 · {len(p1_feats)}</h5>
              <div class="phase-feat-grid">{feat_chips(p1_feats)}</div>
            </div>
            <div class="phase-block phase-kpi">
              <h5>当期 KPI</h5>
              <ol>
                <li>投诉未结样本：续费把关「不允许触达」命中率 = 100%</li>
                <li>工具调用一律走统一注册，无私有取数旁路</li>
                <li>标签字典覆盖投诉 / 风险主标签</li>
                <li>关键运行可在运维台按运行编号查步骤与调用链</li>
                <li>投诉填单与续费把关两次独立运行，无自动联跑</li>
              </ol>
            </div>
          </article>

          <article class="phase-panel">
            <header class="phase-panel-head">
              <span class="phase-num">02</span>
              <div>
                <h4>二期 · 部门功能扩展</h4>
                <p>按部门挂载 · 可测 ROI</p>
              </div>
            </header>
            <div class="phase-block">
              <h5>平台推进</h5>
              <div class="phase-chips">
                <span>补全流程说明书</span>
                <span>扩展 Act / Extract 能力包</span>
                <span>外呼任务仍不联跑上游</span>
              </div>
            </div>
            <div class="phase-block">
              <h5>本期功能 · {len(p2_feats)}</h5>
              <div class="phase-feat-grid">{feat_chips(p2_feats)}</div>
            </div>
            <div class="phase-block phase-kpi">
              <h5>组合 KPI</h5>
              <ol>
                <li>新能力包上线周期 ≤ 原烟囱项目 50%</li>
                <li>政策 / 渠道自助答疑占比提升</li>
                <li>重复工具实现数归零</li>
              </ol>
            </div>
          </article>

          <article class="phase-panel">
            <header class="phase-panel-head">
              <span class="phase-num">03</span>
              <div>
                <h4>三期 · 感知与评测</h4>
                <p>质量闭环 · 合规基线</p>
              </div>
            </header>
            <div class="phase-block">
              <h5>平台推进</h5>
              <div class="phase-chips">
                <span>影像识别扩展位</span>
                <span>金标评测集</span>
                <span>审计报表</span>
                <span>不建企业级单编排器</span>
              </div>
            </div>
            <div class="phase-block">
              <h5>本期功能 · {len(p3_feats)}</h5>
              <div class="phase-feat-grid">{feat_chips(p3_feats)}</div>
            </div>
            <div class="phase-block phase-kpi">
              <h5>组合 KPI</h5>
              <ol>
                <li>质检漏检率、停机响应达到业务基线</li>
                <li>合规抽检通过率达标</li>
                <li>关键业务线形成可复盘的评测基线</li>
              </ol>
            </div>
          </article>
        </div>
      </section>

      <div class="logic-footer-nav">
        <a href="/logic/architecture">← 子页一</a>
        <a href="/logic/risk">进入子页三 →</a>
      </div>
"""
    return shell("青枢出行 · 子页二 · AI 方案设计", body)


def main() -> None:
    by: dict[str, list] = defaultdict(list)
    for f in FEATURES:
        by[f["department_id"]].append(f)

    arch = build_architecture(by)
    sol = build_solution(by)
    (UI / "logic-architecture.html").write_text(arch, encoding="utf-8")
    (UI / "logic-solution.html").write_text(sol, encoding="utf-8")

    # bump css cache on overview/risk too
    for name in ("logic.html", "logic-risk.html"):
        p = UI / name
        t = p.read_text(encoding="utf-8")
        for old in ("20260808-logic1", "20260808-logic2", "20260808-logic3", "20260808-logic4"):
            t = t.replace(f"v={old}", f"v={V}")
        p.write_text(t, encoding="utf-8")

    print("OK", "features", len(FEATURES), "arch", len(arch), "sol", len(sol))


if __name__ == "__main__":
    main()
