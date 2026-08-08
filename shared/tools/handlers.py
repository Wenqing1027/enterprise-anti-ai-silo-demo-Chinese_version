"""全部业务 Tool 实现（只在此处定义一次，经 ToolRegistry 暴露）。

治理三类（read / knowledge / write_govern）在 shared/tools/governance.py 映射，
注册时写入 ToolSpec.tool_class；本文件 category 仍为业务域次级标签，不拆文件。
"""

from __future__ import annotations

import re
from typing import Any, Callable

from shared.datafetcher.fetcher import DataFetcher
from shared.models.enums import StepStatus
from shared.store.store import SharedStore
from shared.tools.base import ToolContext, ToolSpec
from shared.tools.guards import (
    BLOCKING_TAGS,
    clamp_limit,
    dump_model,
    guard_customer_id,
    guard_kb_domain,
    guard_payload,
    guard_text,
    guard_vin,
)

Handler = Callable[..., dict[str, Any]]


# ---------------------------------------------------------------------------
# keyword rules for extraction / tagging (Demo 级，无 LLM)
# ---------------------------------------------------------------------------

_TAG_RULES: list[tuple[str, list[str]]] = [
    ("TAG-投诉未结", ["投诉未结", "一直没处理", "超过7天", "多次投诉", "未结"]),
    ("TAG-三包争议", ["三包", "拒保", "不给换"]),
    ("TAG-续航短", ["续航", "跑不到", "掉电快", "标称"]),
    ("TAG-动力弱", ["没力", "动力弱", "爬坡困难"]),
    ("TAG-异响", ["异响", "噪音", "吱吱"]),
    ("TAG-刹车", ["刹车", "刹不住"]),
    ("TAG-充电慢", ["充电慢", "充不满"]),
    ("TAG-绑车失败", ["绑车", "绑定失败"]),
    ("TAG-上门慢", ["上门慢", "一直不来"]),
    ("TAG-态度差", ["态度差", "骂人", "不耐烦"]),
    ("TAG-舆情风险", ["曝光", "媒体", "报警", "12315"]),
    ("TAG-安全隐患", ["起火", "冒烟", "自燃", "漏电"]),
    ("TAG-电池鼓包", ["鼓包", "温升", "发烫"]),
]

_FAULT_RULES: list[tuple[str, list[str]]] = [
    ("battery", ["电池", "续航", "掉电", "SOH"]),
    ("motor", ["电机", "异响", "限速"]),
    ("brake", ["刹车"]),
    ("controller", ["控制器"]),
    ("charging", ["充电"]),
    ("dashboard", ["仪表", "黑屏"]),
]


def _suggest_tag(text: str) -> tuple[str, str]:
    low = text.lower()
    for tag_id, kws in _TAG_RULES:
        if any(k.lower() in low or k in text for k in kws):
            sentiment = "neg" if tag_id.startswith("TAG-") else "neu"
            if tag_id in {"TAG-投诉未结", "TAG-舆情风险", "TAG-安全隐患", "TAG-三包争议"}:
                sentiment = "neg"
            return tag_id, sentiment
    return "TAG-续航短", "neu"


def _suggest_fault(text: str) -> str:
    for fault, kws in _FAULT_RULES:
        if any(k in text for k in kws):
            return fault
    return "other"


def _suggest_ticket_type(text: str) -> str:
    if any(k in text for k in ("投诉", "曝光", "12315", "态度")):
        return "complaint"
    if any(k in text for k in ("怎么", "如何", "咨询", "问一下")):
        return "consult"
    return "fault"


def build_tool_specs(fetcher: DataFetcher, store: SharedStore) -> list[ToolSpec]:
    """构造全量 ToolSpec（闭包绑定 fetcher/store）。"""

    def get_customer(customer_id: str, **_: Any) -> dict[str, Any]:
        cid = guard_customer_id(customer_id)
        row = fetcher.get_customer(cid)  # type: ignore[arg-type]
        return {"customer": dump_model(row), "found": row is not None}

    def get_vehicle(vin: str, **_: Any) -> dict[str, Any]:
        v = guard_vin(vin)
        row = fetcher.get_vehicle(v)  # type: ignore[arg-type]
        return {"vehicle": dump_model(row), "found": row is not None}

    def list_vehicles(
        customer_id: str | None = None,
        model: str | None = None,
        limit: int = 20,
        **_: Any,
    ) -> dict[str, Any]:
        cid = guard_customer_id(customer_id) if customer_id else None
        rows = fetcher.list_vehicles(customer_id=cid, model=model, limit=clamp_limit(limit))
        return {"vehicles": dump_model(rows), "count": len(rows)}

    def get_dealer(dealer_id: str, **_: Any) -> dict[str, Any]:
        row = fetcher.get_dealer(str(dealer_id))
        return {"dealer": dump_model(row), "found": row is not None}

    def get_store(store_id: str, **_: Any) -> dict[str, Any]:
        row = fetcher.get_store(str(store_id))
        return {"store": dump_model(row), "found": row is not None}

    def list_stores(dealer_id: str | None = None, **_: Any) -> dict[str, Any]:
        rows = fetcher.list_stores(dealer_id=dealer_id)
        return {"stores": dump_model(rows), "count": len(rows)}

    def get_sku(sku_id: str, **_: Any) -> dict[str, Any]:
        row = fetcher.get_sku(str(sku_id))
        return {"sku": dump_model(row), "found": row is not None}

    def get_org(org_id: str, **_: Any) -> dict[str, Any]:
        row = fetcher.get_org(str(org_id))
        return {"org": dump_model(row), "found": row is not None}

    def list_regions(**_: Any) -> dict[str, Any]:
        rows = fetcher.list_regions()
        return {"regions": dump_model(rows), "count": len(rows)}

    def get_order(order_id: str, **_: Any) -> dict[str, Any]:
        row = fetcher.get_order(str(order_id))
        return {"order": dump_model(row), "found": row is not None}

    def list_orders(
        dealer_id: str | None = None,
        store_id: str | None = None,
        sku_id: str | None = None,
        limit: int = 20,
        **_: Any,
    ) -> dict[str, Any]:
        rows = fetcher.list_orders(
            dealer_id=dealer_id,
            store_id=store_id,
            sku_id=sku_id,
            limit=clamp_limit(limit),
        )
        return {"orders": dump_model(rows), "count": len(rows)}

    def list_inventory(
        sku_id: str | None = None,
        store_id: str | None = None,
        dealer_id: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        rows = fetcher.list_inventory(sku_id=sku_id, store_id=store_id, dealer_id=dealer_id)
        return {"inventory": dump_model(rows), "count": len(rows)}

    def get_policy(dealer_id: str, **_: Any) -> dict[str, Any]:
        row = fetcher.get_policy(str(dealer_id))
        return {"policy": dump_model(row), "found": row is not None}

    def simulate_rebate_tier(
        dealer_id: str,
        extra_qty: int = 0,
        **_: Any,
    ) -> dict[str, Any]:
        """政策模拟：再提 X 台到下一档（Demo 规则表）。"""
        policy = fetcher.get_policy(str(dealer_id))
        if not policy:
            return {"found": False, "message": "policy not found"}
        tiers = [
            ("铜牌", 300, 0.020),
            ("银牌", 800, 0.035),
            ("金牌", 1200, 0.042),
            ("钻石", 1800, 0.050),
        ]
        current_qty = int(policy.current_pickup_qty_mtd or 0)
        sim_qty = current_qty + int(extra_qty)
        current_tier = "未达档"
        current_rate = 0.0
        next_tier = None
        qty_to_next = None
        for name, thr, rate in tiers:
            if sim_qty >= thr:
                current_tier, current_rate = name, rate
        for name, thr, rate in tiers:
            if sim_qty < thr:
                next_tier = name
                qty_to_next = thr - sim_qty
                break
        predicted_rebate = round(sim_qty * 3299 * current_rate, 2)
        return {
            "found": True,
            "dealer_id": dealer_id,
            "current_pickup_qty_mtd": current_qty,
            "simulate_extra_qty": int(extra_qty),
            "simulated_qty": sim_qty,
            "current_tier_after_sim": current_tier,
            "rebate_rate": current_rate,
            "next_tier_name": next_tier,
            "qty_to_next_tier": qty_to_next,
            "predicted_rebate_amt": predicted_rebate,
            "policy_version": policy.policy_version,
        }

    def list_color_plans(week: str | None = None, **_: Any) -> dict[str, Any]:
        rows = fetcher.list_color_plans(week=week)
        return {"color_plans": dump_model(rows), "count": len(rows)}

    def get_ticket(ticket_id: str, **_: Any) -> dict[str, Any]:
        row = fetcher.get_ticket(str(ticket_id))
        return {"ticket": dump_model(row), "found": row is not None}

    def list_tickets(
        customer_id: str | None = None,
        vin: str | None = None,
        ticket_status: str | None = None,
        tag_id: str | None = None,
        limit: int = 20,
        **_: Any,
    ) -> dict[str, Any]:
        cid = guard_customer_id(customer_id) if customer_id else None
        v = guard_vin(vin) if vin else None
        rows = fetcher.list_tickets(
            customer_id=cid,
            vin=v,
            ticket_status=ticket_status,
            tag_id=tag_id,
            limit=clamp_limit(limit),
        )
        return {"tickets": dump_model(rows), "count": len(rows)}

    def extract_ticket_fields(
        text: str,
        customer_id: str | None = None,
        vin: str | None = None,
        channel: str | None = "400",
        **_: Any,
    ) -> dict[str, Any]:
        body = guard_text(text)
        cid = guard_customer_id(customer_id) if customer_id else None
        v = guard_vin(vin) if vin else None
        # 尝试从文本抽 QS0 VIN / CUS- id
        if not v:
            m = re.search(r"QS0[A-Z0-9]{14}", body.upper())
            if m:
                v = guard_vin(m.group(0))
        if not cid:
            m = re.search(r"CUS-\d+", body.upper())
            if m:
                cid = guard_customer_id(m.group(0))
        tag_id, sentiment = _suggest_tag(body)
        draft = {
            "customer_id": cid,
            "vin": v,
            "ticket_type": _suggest_ticket_type(body),
            "fault_category": _suggest_fault(body),
            "ticket_channel": channel or "400",
            "ticket_status": "open",
            "tag_id": tag_id,
            "sentiment": sentiment,
            "desc_text": body[:1000],
            "is_complaint": _suggest_ticket_type(body) == "complaint"
            or tag_id in BLOCKING_TAGS,
        }
        return {"ticket_draft": draft, "rule_based": True}

    def list_voc(
        customer_id: str | None = None,
        tag_id: str | None = None,
        limit: int = 20,
        **_: Any,
    ) -> dict[str, Any]:
        cid = guard_customer_id(customer_id) if customer_id else None
        rows = fetcher.list_voc(customer_id=cid, tag_id=tag_id, limit=clamp_limit(limit))
        return {"voc": dump_model(rows), "count": len(rows)}

    def suggest_voc_tags(text: str, **_: Any) -> dict[str, Any]:
        body = guard_text(text)
        tag_id, sentiment = _suggest_tag(body)
        tag = fetcher.get_tag(tag_id)
        return {
            "tag_id": tag_id,
            "sentiment": sentiment,
            "tag": dump_model(tag),
            "rule_based": True,
        }

    def get_renewal(
        customer_id: str,
        vin: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        cid = guard_customer_id(customer_id)
        v = guard_vin(vin) if vin else None
        row = fetcher.get_renewal(cid, v)  # type: ignore[arg-type]
        return {"renewal": dump_model(row), "found": row is not None}

    def score_renewal(
        customer_id: str,
        vin: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        cid = guard_customer_id(customer_id)
        v = guard_vin(vin) if vin else None
        renewal = fetcher.get_renewal(cid, v)  # type: ignore[arg-type]
        behavior = fetcher.get_user_behavior(cid, v)  # type: ignore[arg-type]
        if not renewal:
            return {"found": False, "score": 0.0, "intent_level": "low"}
        base = float(renewal.renew_intent_score or 0.3)
        if renewal.active_t7_flag:
            base += 0.15
        elif renewal.active_t30_flag:
            base += 0.08
        if renewal.sleep_90d_app_flag:
            base -= 0.12
        if behavior and behavior.rfm_segment and str(behavior.rfm_segment) == "high_value":
            base += 0.1
        score = max(0.0, min(0.99, round(base, 2)))
        level = "high" if score >= 0.7 else ("mid" if score >= 0.4 else "low")
        return {
            "found": True,
            "customer_id": cid,
            "vin": renewal.vin,
            "score": score,
            "intent_level": level,
            "renew_pool_layer": renewal.renew_pool_layer,
        }

    def route_renewal_pool(
        customer_id: str,
        vin: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        cid = guard_customer_id(customer_id)
        v = guard_vin(vin) if vin else None
        renewal = fetcher.get_renewal(cid, v)  # type: ignore[arg-type]
        if not renewal:
            return {"found": False}
        layer = str(renewal.renew_pool_layer or "sleep")
        # 触达阶梯：Push → 短信 → AI外呼 → 人工
        channel_plan = {
            "T-7": ["push", "sms", "ai_call"],
            "T-30": ["push", "sms"],
            "sleep": ["push"],
            "non_smart": ["push"],
        }.get(layer, ["push"])
        return {
            "found": True,
            "customer_id": cid,
            "vin": renewal.vin,
            "renew_pool_layer": layer,
            "channel_plan": channel_plan,
            "max_touches_per_day": 3,
            "note": "非智能车不算续费率分母；触达前必须检查阻断标签",
        }

    def check_outreach_block(
        customer_id: str,
        vin: str | None = None,
        consumer_skill: str = "renewal_plan",
        **_: Any,
    ) -> dict[str, Any]:
        """Story2 关键：共享层是否存在应阻断触达的标签。"""
        cid = guard_customer_id(customer_id)
        v = guard_vin(vin) if vin else None
        blocked, tags = store.has_blocking_tag(
            customer_id=cid,
            vin=v,
            consumer_skill=consumer_skill,
        )
        reason = None
        if blocked:
            reason = "存在阻断标签：" + "、".join(tags)
        return {
            "customer_id": cid,
            "vin": v,
            "allow_outreach": not blocked,
            "blocked": blocked,
            "blocking_tags": tags,
            "block_reason": reason,
        }

    def get_user_behavior(
        customer_id: str,
        vin: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        cid = guard_customer_id(customer_id)
        v = guard_vin(vin) if vin else None
        row = fetcher.get_user_behavior(cid, v)  # type: ignore[arg-type]
        return {"user_behavior": dump_model(row), "found": row is not None}

    def _assert_kb_domain_allowed(
        domain: str | None,
        _context: ToolContext | None,
        *,
        tool_name: str,
    ) -> str | None:
        """Skill 级 kb 域闸门（防 search 漏域 / get_kb_document 绕域）。"""
        allow = list(_context.kb_domains_allow) if _context and _context.kb_domains_allow else []
        d = guard_kb_domain(domain)
        if not allow:
            return d
        if d is None:
            if len(allow) == 1:
                return allow[0]
            from shared.tools.base import ToolError

            raise ToolError(
                f"{tool_name}: domain required; allowed={allow}",
                code="KB_DOMAIN_REQUIRED",
            )
        if d not in allow:
            from shared.tools.base import ToolError

            raise ToolError(
                f"{tool_name}: domain={d} not in allowed={allow}",
                code="KB_DOMAIN_DENIED",
            )
        return d

    def search_kb(
        query: str,
        domain: str | None = None,
        top_k: int = 5,
        _context: ToolContext | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        q = guard_text(query, field="query")
        d = _assert_kb_domain_allowed(domain, _context, tool_name="search_kb")
        k = clamp_limit(top_k, default=5)
        hits = fetcher.search_kb(q, domain=d, top_k=min(k, 10))
        # 双保险：即使底层忽略 domain，也按 allow 过滤
        allow = list(_context.kb_domains_allow) if _context and _context.kb_domains_allow else []
        if allow:
            filtered = []
            for h in hits:
                hd = getattr(h, "kb_domain", None)
                if hd is None and isinstance(h, dict):
                    hd = h.get("kb_domain")
                if hd in allow:
                    filtered.append(h)
            hits = filtered
        return {"hits": dump_model(hits), "count": len(hits), "domain": d}

    def get_kb_document(
        kb_doc_id: str,
        _context: ToolContext | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        row = fetcher.get_kb_document(str(kb_doc_id))
        if row is not None and _context and _context.kb_domains_allow:
            domain = getattr(row, "kb_domain", None)
            if domain is None and isinstance(row, dict):
                domain = row.get("kb_domain")
            _assert_kb_domain_allowed(
                str(domain) if domain else None,
                _context,
                tool_name="get_kb_document",
            )
        return {"document": dump_model(row), "found": row is not None}

    def list_kb_domains(_context: ToolContext | None = None, **_: Any) -> dict[str, Any]:
        domains = fetcher.list_kb_domains()
        allow = list(_context.kb_domains_allow) if _context and _context.kb_domains_allow else []
        if allow:
            domains = [d for d in domains if d in allow]
        return {"domains": domains}

    def write_ai_output(
        producer_skill: str,
        payload: dict[str, Any] | list[Any],
        consumer_allow: list[str] | None = None,
        run_id: str | None = None,
        payload_schema: str | None = None,
        _context: ToolContext | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        skill = guard_text(producer_skill, field="producer_skill")
        # 限制：上下文 skill 与 producer 必须一致，防跨 Skill 冒充写入
        if _context and _context.skill_id and _context.skill_id != skill:
            from shared.tools.base import ToolError

            raise ToolError(
                f"producer_skill must match context.skill_id={_context.skill_id}",
                code="PRODUCER_MISMATCH",
            )
        body = guard_payload(payload)
        allow = list(consumer_allow or [])
        if isinstance(body, dict):
            # 规范化关联键
            if body.get("vin"):
                body["vin"] = guard_vin(str(body["vin"]))
            if body.get("customer_id"):
                body["customer_id"] = guard_customer_id(str(body["customer_id"]))
        rid = run_id or (_context.run_id if _context else None)
        out = store.write_ai_output(
            producer_skill=skill,
            payload=body,
            consumer_allow=allow,
            run_id=rid,
            payload_schema=payload_schema,
        )
        return {"ai_output": dump_model(out)}

    def read_ai_outputs(
        consumer_skill: str | None = None,
        producer_skill: str | None = None,
        customer_id: str | None = None,
        vin: str | None = None,
        tag_id: str | None = None,
        run_id: str | None = None,
        limit: int = 20,
        _context: ToolContext | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        cid = guard_customer_id(customer_id) if customer_id else None
        v = guard_vin(vin) if vin else None
        consumer = consumer_skill or (_context.skill_id if _context else None)
        rows = store.read_ai_outputs(
            consumer_skill=consumer,
            producer_skill=producer_skill,
            customer_id=cid,
            vin=v,
            tag_id=tag_id,
            run_id=run_id,
            limit=clamp_limit(limit),
        )
        return {"ai_outputs": dump_model(rows), "count": len(rows)}

    def read_shared_tags(
        customer_id: str | None = None,
        vin: str | None = None,
        consumer_skill: str | None = None,
        _context: ToolContext | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        cid = guard_customer_id(customer_id) if customer_id else None
        v = guard_vin(vin) if vin else None
        consumer = consumer_skill or (_context.skill_id if _context else None)
        tags = store.read_shared_tags(
            consumer_skill=consumer,
            customer_id=cid,
            vin=v,
        )
        return {"tags": tags, "count": len(tags)}

    def get_ai_output(ai_output_id: str, **_: Any) -> dict[str, Any]:
        row = store.get_ai_output(str(ai_output_id))
        return {"ai_output": dump_model(row), "found": row is not None}

    def list_capabilities(**_: Any) -> dict[str, Any]:
        rows = fetcher.list_capabilities()
        return {"capabilities": dump_model(rows), "count": len(rows)}

    def get_capability(skill_id: str, **_: Any) -> dict[str, Any]:
        row = fetcher.get_capability(str(skill_id))
        return {"capability": dump_model(row), "found": row is not None}

    def get_tag(tag_id: str, **_: Any) -> dict[str, Any]:
        row = fetcher.get_tag(str(tag_id))
        return {"tag": dump_model(row), "found": row is not None}

    def list_tags(domain: str | None = None, **_: Any) -> dict[str, Any]:
        rows = fetcher.list_tags(domain=domain)
        return {"tags": dump_model(rows), "count": len(rows)}

    def log_step(
        step_name: str,
        run_id: str | None = None,
        step_status: str = "ok",
        detail: dict[str, Any] | None = None,
        _context: ToolContext | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        name = guard_text(step_name, field="step_name")
        rid = run_id or (_context.run_id if _context else None)
        if not rid:
            from shared.tools.base import ToolError

            raise ToolError("run_id is required (arg or context)", code="MISSING_RUN_ID")
        status = StepStatus(step_status) if step_status in {s.value for s in StepStatus} else StepStatus.OK
        entry = store.log_step(
            run_id=rid,
            step_name=name,
            step_status=status,
            detail=detail if isinstance(detail, dict) or detail is None else {"value": detail},
        )
        return {"run_log": dump_model(entry)}

    def list_run_logs(run_id: str | None = None, **_: Any) -> dict[str, Any]:
        rows = store.list_run_logs(run_id=run_id)
        return {"run_logs": dump_model(rows), "count": len(rows)}

    def get_dealer_health(dealer_id: str, **_: Any) -> dict[str, Any]:
        row = fetcher.get_dealer_health(str(dealer_id))
        return {"health": dump_model(row), "found": row is not None}

    def list_alerts(dealer_id: str | None = None, **_: Any) -> dict[str, Any]:
        rows = fetcher.list_alerts(dealer_id=dealer_id)
        return {"alerts": dump_model(rows), "count": len(rows)}

    def list_sales_metrics(org_id: str | None = None, **_: Any) -> dict[str, Any]:
        rows = fetcher.list_sales_metrics(org_id=org_id)
        return {"sales_metrics": dump_model(rows), "count": len(rows)}

    def list_retail_daily(store_id: str | None = None, **_: Any) -> dict[str, Any]:
        rows = fetcher.list_retail_daily(store_id=store_id)
        return {"retail_daily": dump_model(rows), "count": len(rows)}

    def list_inspections(store_id: str | None = None, **_: Any) -> dict[str, Any]:
        rows = fetcher.list_inspections(store_id=store_id)
        return {"inspections": dump_model(rows), "count": len(rows)}

    def get_risk(dealer_id: str, **_: Any) -> dict[str, Any]:
        row = fetcher.get_risk(str(dealer_id))
        return {"risk": dump_model(row), "found": row is not None}

    def list_campaigns(**_: Any) -> dict[str, Any]:
        rows = fetcher.list_campaigns()
        return {"campaigns": dump_model(rows), "count": len(rows)}

    def get_telemetry(vin: str, **_: Any) -> dict[str, Any]:
        v = guard_vin(vin)
        row = fetcher.get_telemetry(v)  # type: ignore[arg-type]
        return {"telemetry": dump_model(row), "found": row is not None}

    def list_quality_checks(vin: str | None = None, **_: Any) -> dict[str, Any]:
        v = guard_vin(vin) if vin else None
        rows = fetcher.list_quality_checks(vin=v)
        return {"quality_checks": dump_model(rows), "count": len(rows)}

    def list_competitors(**_: Any) -> dict[str, Any]:
        rows = fetcher.list_competitors()
        return {"competitors": dump_model(rows), "count": len(rows)}

    # ---- register specs ----
    def p(props: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": props,
            "required": required or [],
            "additionalProperties": False,
        }

    S = ToolSpec
    return [
        # 主数据
        S("get_customer", "查询客户主数据", p({"customer_id": {"type": "string"}}, ["customer_id"]), get_customer, True, "master", ["customer_id"]),
        S("get_vehicle", "查询车辆（VIN 须为 QS0 合成号）", p({"vin": {"type": "string"}}, ["vin"]), get_vehicle, True, "master", ["vin"]),
        S("list_vehicles", "按客户/车型列出车辆", p({"customer_id": {"type": "string"}, "model": {"type": "string"}, "limit": {"type": "integer"}}), list_vehicles, True, "master"),
        S("get_dealer", "查询一代经销商", p({"dealer_id": {"type": "string"}}, ["dealer_id"]), get_dealer, True, "master", ["dealer_id"]),
        S("get_store", "查询门店", p({"store_id": {"type": "string"}}, ["store_id"]), get_store, True, "master", ["store_id"]),
        S("list_stores", "列出门店", p({"dealer_id": {"type": "string"}}), list_stores, True, "master"),
        S("get_sku", "查询 SKU", p({"sku_id": {"type": "string"}}, ["sku_id"]), get_sku, True, "master", ["sku_id"]),
        S("get_org", "查询组织节点", p({"org_id": {"type": "string"}}, ["org_id"]), get_org, True, "master", ["org_id"]),
        S("list_regions", "列出行政区", p({}), list_regions, True, "master"),
        S("list_competitors", "列出竞品快照（虚构品牌）", p({}), list_competitors, True, "master"),
        # 交易
        S("get_order", "查询订单", p({"order_id": {"type": "string"}}, ["order_id"]), get_order, True, "commerce", ["order_id"]),
        S("list_orders", "筛选订单列表", p({"dealer_id": {"type": "string"}, "store_id": {"type": "string"}, "sku_id": {"type": "string"}, "limit": {"type": "integer"}}), list_orders, True, "commerce"),
        S("list_inventory", "查询库存", p({"sku_id": {"type": "string"}, "store_id": {"type": "string"}, "dealer_id": {"type": "string"}}), list_inventory, True, "commerce"),
        S("get_policy", "查询经销商返利政策摘要", p({"dealer_id": {"type": "string"}}, ["dealer_id"]), get_policy, True, "commerce", ["dealer_id"]),
        S("simulate_rebate_tier", "模拟再提货冲档返利", p({"dealer_id": {"type": "string"}, "extra_qty": {"type": "integer"}}, ["dealer_id"]), simulate_rebate_tier, True, "commerce", ["dealer_id"]),
        S("list_color_plans", "查询颜色排产计划", p({"week": {"type": "string"}}), list_color_plans, True, "commerce"),
        # 服务 / VoC
        S("get_ticket", "查询工单", p({"ticket_id": {"type": "string"}}, ["ticket_id"]), get_ticket, True, "service", ["ticket_id"]),
        S("list_tickets", "筛选工单", p({"customer_id": {"type": "string"}, "vin": {"type": "string"}, "ticket_status": {"type": "string"}, "tag_id": {"type": "string"}, "limit": {"type": "integer"}}), list_tickets, True, "service"),
        S("extract_ticket_fields", "【ReAct 规则工具】从文本抽工单草案字段；并行 Extraction Agent 请用 skill ticket_fields（POST /v1/extraction/runs）", p({"text": {"type": "string"}, "customer_id": {"type": "string"}, "vin": {"type": "string"}, "channel": {"type": "string"}}, ["text"]), extract_ticket_fields, True, "service", ["text"]),
        S("list_voc", "查询 VoC 反馈切片", p({"customer_id": {"type": "string"}, "tag_id": {"type": "string"}, "limit": {"type": "integer"}}), list_voc, True, "service"),
        S("suggest_voc_tags", "建议 VoC 标签与情感（规则）", p({"text": {"type": "string"}}, ["text"]), suggest_voc_tags, True, "service", ["text"]),
        # 续费
        S("get_renewal", "查询续费池记录", p({"customer_id": {"type": "string"}, "vin": {"type": "string"}}, ["customer_id"]), get_renewal, True, "renewal", ["customer_id"]),
        S("score_renewal", "计算续费意向分", p({"customer_id": {"type": "string"}, "vin": {"type": "string"}}, ["customer_id"]), score_renewal, True, "renewal", ["customer_id"]),
        S("route_renewal_pool", "续费池分流与触达阶梯", p({"customer_id": {"type": "string"}, "vin": {"type": "string"}}, ["customer_id"]), route_renewal_pool, True, "renewal", ["customer_id"]),
        S("check_outreach_block", "检查共享标签是否阻断触达（Story2）", p({"customer_id": {"type": "string"}, "vin": {"type": "string"}, "consumer_skill": {"type": "string"}}, ["customer_id"]), check_outreach_block, True, "renewal", ["customer_id"]),
        S("get_user_behavior", "查询用户行为/RFM", p({"customer_id": {"type": "string"}, "vin": {"type": "string"}}, ["customer_id"]), get_user_behavior, True, "renewal", ["customer_id"]),
        # 知识库
        S("search_kb", "检索知识库", p({"query": {"type": "string"}, "domain": {"type": "string"}, "top_k": {"type": "integer"}}, ["query"]), search_kb, True, "knowledge", ["query"]),
        S("get_kb_document", "获取知识库全文", p({"kb_doc_id": {"type": "string"}}, ["kb_doc_id"]), get_kb_document, True, "knowledge", ["kb_doc_id"]),
        S("list_kb_domains", "列出知识库域", p({}), list_kb_domains, True, "knowledge"),
        # 共享层
        S("write_ai_output", "写入共享 AI 产出（资产化）", p({"producer_skill": {"type": "string"}, "payload": {"type": "object"}, "consumer_allow": {"type": "array"}, "run_id": {"type": "string"}, "payload_schema": {"type": "string"}}, ["producer_skill", "payload"]), write_ai_output, False, "shared", ["producer_skill", "payload"]),
        S("read_ai_outputs", "读取共享 AI 产出", p({"consumer_skill": {"type": "string"}, "producer_skill": {"type": "string"}, "customer_id": {"type": "string"}, "vin": {"type": "string"}, "tag_id": {"type": "string"}, "run_id": {"type": "string"}, "limit": {"type": "integer"}}), read_ai_outputs, True, "shared"),
        S("read_shared_tags", "读取共享标签投影", p({"customer_id": {"type": "string"}, "vin": {"type": "string"}, "consumer_skill": {"type": "string"}}), read_shared_tags, True, "shared"),
        S("get_ai_output", "按 ID 获取 AI 产出", p({"ai_output_id": {"type": "string"}}, ["ai_output_id"]), get_ai_output, True, "shared", ["ai_output_id"]),
        S("list_capabilities", "列出 Skill 能力目录", p({}), list_capabilities, True, "shared"),
        S("get_capability", "查询单个 Skill 能力", p({"skill_id": {"type": "string"}}, ["skill_id"]), get_capability, True, "shared", ["skill_id"]),
        S("get_tag", "查询标签字典项", p({"tag_id": {"type": "string"}}, ["tag_id"]), get_tag, True, "shared", ["tag_id"]),
        S("list_tags", "列出标签", p({"domain": {"type": "string"}}), list_tags, True, "shared"),
        S("log_step", "记录运行步骤日志", p({"step_name": {"type": "string"}, "run_id": {"type": "string"}, "step_status": {"type": "string"}, "detail": {"type": "object"}}, ["step_name"]), log_step, False, "shared", ["step_name"]),
        S("list_run_logs", "列出运行步骤日志", p({"run_id": {"type": "string"}}), list_run_logs, True, "shared"),
        # 渠道经营 / 质检 / IoT
        S("get_dealer_health", "一代经营健康指数", p({"dealer_id": {"type": "string"}}, ["dealer_id"]), get_dealer_health, True, "channel", ["dealer_id"]),
        S("list_alerts", "经营预警列表", p({"dealer_id": {"type": "string"}}), list_alerts, True, "channel"),
        S("list_sales_metrics", "销量达成指标", p({"org_id": {"type": "string"}}), list_sales_metrics, True, "channel"),
        S("list_retail_daily", "门店零售日报切片", p({"store_id": {"type": "string"}}), list_retail_daily, True, "channel"),
        S("list_inspections", "门店巡检记录", p({"store_id": {"type": "string"}}), list_inspections, True, "channel"),
        S("get_risk", "加盟/合作风控摘要", p({"dealer_id": {"type": "string"}}, ["dealer_id"]), get_risk, True, "channel", ["dealer_id"]),
        S("list_campaigns", "营销活动列表", p({}), list_campaigns, True, "channel"),
        S("get_telemetry", "车辆 IoT 遥测/告警", p({"vin": {"type": "string"}}, ["vin"]), get_telemetry, True, "iot", ["vin"]),
        S("list_quality_checks", "质检记录", p({"vin": {"type": "string"}}), list_quality_checks, True, "iot"),
    ]
