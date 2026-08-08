"""Plan 控制环：读共享 → 闸门 → 结构化计划/阻断说明。

B1 瘦实现：少工具、可不调 LLM；另一次独立运行，不接上游 Agent 话筒。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from agents.planning.skill_loader import load_planning_skill
from shared.tools.base import ToolContext
from shared.tools.registry import ToolRegistry, default_registry


@dataclass
class PlanResult:
    ok: bool
    skill_id: str
    run_id: str
    stop_reason: str
    control_loop: str = "plan"
    customer_id: str | None = None
    vin: str | None = None
    gate: dict[str, Any] = field(default_factory=dict)
    plan: dict[str, Any] | None = None
    final_answer: str = ""
    steps: list[dict[str, Any]] = field(default_factory=list)
    shared_tag_ids: list[str] = field(default_factory=list)
    ai_output_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "skill_id": self.skill_id,
            "run_id": self.run_id,
            "stop_reason": self.stop_reason,
            "control_loop": self.control_loop,
            "customer_id": self.customer_id,
            "vin": self.vin,
            "gate": self.gate,
            "plan": self.plan,
            "final_answer": self.final_answer,
            "steps": self.steps,
            "shared_tag_ids": self.shared_tag_ids,
            "ai_output_ids": self.ai_output_ids,
        }


def _normalize_input(user_input: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(user_input, dict):
        body = user_input.get("input") if isinstance(user_input.get("input"), dict) else user_input
        assert isinstance(body, dict)
        return {
            "customer_id": str(body.get("customer_id") or "").strip() or None,
            "vin": str(body.get("vin") or "").strip() or None,
            "text": str(body.get("text") or body.get("query") or "").strip(),
        }
    text = str(user_input or "").strip()
    return {"customer_id": None, "vin": None, "text": text}


def _step(
    steps: list[dict[str, Any]],
    *,
    name: str,
    ok: bool,
    phase: str,
    detail: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    steps.append(
        {
            "step": len(steps) + 1,
            "name": name,
            "phase": phase,
            "ok": ok,
            "detail": detail or {},
            "error": error,
        }
    )


class PlanningAgent:
    """读共享标签 → check_outreach_block → 结构化 gate/plan。"""

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self.registry = registry or default_registry

    def run(
        self,
        skill_id: str,
        user_input: str | dict[str, Any],
        *,
        run_id: str | None = None,
    ) -> PlanResult:
        cfg = load_planning_skill(skill_id)
        rid = run_id or f"plan-{uuid.uuid4().hex[:10]}"
        steps: list[dict[str, Any]] = []
        inp = _normalize_input(user_input)
        customer_id = inp.get("customer_id")
        vin = inp.get("vin")

        ctx = ToolContext(
            run_id=rid,
            skill_id=skill_id,
            agent_type="plan",
            allowed_tools=list(cfg.allowed_tools),
        )

        if not customer_id:
            _step(
                steps,
                name="plan_validate_input",
                ok=False,
                phase="validate",
                error="customer_id required",
            )
            return PlanResult(
                ok=False,
                skill_id=skill_id,
                run_id=rid,
                stop_reason="missing_customer_id",
                customer_id=None,
                vin=vin,
                gate={"blocked": None, "allow_outreach": None, "reason": "缺少 customer_id"},
                final_answer="Plan 需要 customer_id 才能读共享标签并做触达闸门。",
                steps=steps,
            )

        self.registry.call(
            "log_step",
            {
                "step_name": "plan_start",
                "run_id": rid,
                "step_status": "ok",
                "detail": {"skill_id": skill_id, "phase": "read_shared"},
            },
            context=ctx,
        )
        _step(
            steps,
            name="plan_start",
            ok=True,
            phase="read_shared",
            detail={"customer_id": customer_id, "vin": vin},
        )

        # 1) 读共享标签
        tags_res = self.registry.call(
            "read_shared_tags",
            {
                "customer_id": customer_id,
                "vin": vin,
                "consumer_skill": skill_id,
            },
            context=ctx,
        )
        tag_ids = [
            str(t.get("tag_id"))
            for t in (tags_res.data or {}).get("tags", [])
            if t.get("tag_id")
        ]
        _step(
            steps,
            name="read_shared_tags",
            ok=tags_res.ok,
            phase="read_shared",
            detail={"count": len(tag_ids), "tag_ids": tag_ids},
            error=None if tags_res.ok else tags_res.error,
        )
        if not tags_res.ok:
            return PlanResult(
                ok=False,
                skill_id=skill_id,
                run_id=rid,
                stop_reason="read_shared_failed",
                customer_id=customer_id,
                vin=vin,
                gate={"blocked": None, "allow_outreach": None, "reason": tags_res.error},
                final_answer=f"读共享标签失败：{tags_res.error}",
                steps=steps,
                shared_tag_ids=tag_ids,
            )

        # 2) 读共享产出（可选，丰富上下文）
        outputs_res = self.registry.call(
            "read_ai_outputs",
            {
                "consumer_skill": skill_id,
                "customer_id": customer_id,
                "vin": vin,
                "limit": 5,
            },
            context=ctx,
        )
        ai_ids: list[str] = []
        if outputs_res.ok:
            for row in (outputs_res.data or {}).get("ai_outputs") or []:
                oid = row.get("ai_output_id") or row.get("id")
                if oid:
                    ai_ids.append(str(oid))
        _step(
            steps,
            name="read_ai_outputs",
            ok=outputs_res.ok,
            phase="read_shared",
            detail={"count": (outputs_res.data or {}).get("count"), "ai_output_ids": ai_ids},
            error=None if outputs_res.ok else outputs_res.error,
        )

        # 3) 闸门
        block_res = self.registry.call(
            "check_outreach_block",
            {
                "customer_id": customer_id,
                "vin": vin,
                "consumer_skill": skill_id,
            },
            context=ctx,
        )
        if not block_res.ok:
            _step(
                steps,
                name="check_outreach_block",
                ok=False,
                phase="gate",
                error=block_res.error,
            )
            return PlanResult(
                ok=False,
                skill_id=skill_id,
                run_id=rid,
                stop_reason="gate_failed",
                customer_id=customer_id,
                vin=vin,
                gate={"blocked": None, "allow_outreach": None, "reason": block_res.error},
                final_answer=f"闸门检查失败：{block_res.error}",
                steps=steps,
                shared_tag_ids=tag_ids,
                ai_output_ids=ai_ids,
            )

        block_data = block_res.data or {}
        blocked = bool(block_data.get("blocked"))
        allow = block_data.get("allow_outreach")
        if allow is None:
            allow = not blocked
        blocking_tags = list(block_data.get("blocking_tags") or [])
        reason = block_data.get("block_reason") or (
            ("存在阻断标签：" + "、".join(blocking_tags)) if blocked else "无阻断标签，允许触达"
        )
        gate = {
            "blocked": blocked,
            "allow_outreach": bool(allow),
            "reason": reason,
            "tag_ids": blocking_tags or tag_ids,
            "blocking_tags": blocking_tags,
        }
        _step(
            steps,
            name="check_outreach_block",
            ok=True,
            phase="gate",
            detail=gate,
        )

        plan: dict[str, Any] | None = None
        if blocked:
            plan = {
                "action": "block_outreach",
                "summary": "因共享层投诉/风险标签，禁止主动续费触达。",
                "next_steps": [
                    "等待服务侧关闭投诉工单并更新共享标签",
                    "人工复核后再评估是否进入续费池触达",
                ],
                "channels": [],
            }
            final = (
                f"【触达闸门 · 阻断】客户 {customer_id} 不允许主动续费触达。\n"
                f"原因：{reason}\n"
                f"共享标签：{', '.join(tag_ids) or '（无）'}\n"
                "说明：本运行独立读共享层，未联跑上游 Agent。"
            )
            stop = "blocked"
        else:
            # 未阻断：续费池 + 评分 + 分流阶梯 → 短触达计划（对应流上 n_gate 同次产出）
            renewal_detail: dict[str, Any] = {}
            if "get_renewal" in cfg.allowed_tools:
                ren = self.registry.call(
                    "get_renewal",
                    {"customer_id": customer_id, "vin": vin},
                    context=ctx,
                )
                _step(
                    steps,
                    name="get_renewal",
                    ok=ren.ok,
                    phase="plan",
                    detail=ren.data if ren.ok else {},
                    error=None if ren.ok else ren.error,
                )
                if ren.ok:
                    renewal_detail = (ren.data or {}).get("renewal") or ren.data or {}

            if "get_user_behavior" in cfg.allowed_tools:
                beh = self.registry.call(
                    "get_user_behavior",
                    {"customer_id": customer_id, "vin": vin},
                    context=ctx,
                )
                _step(
                    steps,
                    name="get_user_behavior",
                    ok=beh.ok,
                    phase="plan",
                    detail=beh.data if beh.ok else {},
                    error=None if beh.ok else beh.error,
                )

            score_detail: dict[str, Any] = {}
            if "score_renewal" in cfg.allowed_tools:
                scored = self.registry.call(
                    "score_renewal",
                    {"customer_id": customer_id, "vin": vin},
                    context=ctx,
                )
                _step(
                    steps,
                    name="score_renewal",
                    ok=scored.ok,
                    phase="plan",
                    detail=scored.data if scored.ok else {},
                    error=None if scored.ok else scored.error,
                )
                if scored.ok:
                    score_detail = scored.data or {}

            route_detail: dict[str, Any] = {}
            if "route_renewal_pool" in cfg.allowed_tools:
                routed = self.registry.call(
                    "route_renewal_pool",
                    {"customer_id": customer_id, "vin": vin},
                    context=ctx,
                )
                _step(
                    steps,
                    name="route_renewal_pool",
                    ok=routed.ok,
                    phase="plan",
                    detail=routed.data if routed.ok else {},
                    error=None if routed.ok else routed.error,
                )
                if routed.ok:
                    route_detail = routed.data or {}

            intent = score_detail.get("score") or renewal_detail.get("renew_intent_score")
            pool = (
                route_detail.get("renew_pool_layer")
                or renewal_detail.get("renew_pool_layer")
                or score_detail.get("pool_layer")
            )
            channels = list(route_detail.get("channel_plan") or [])
            if not channels:
                channels = ["push", "sms"] if pool in ("T-7", "T-30") else ["push"]
            intent_level = score_detail.get("intent_level") or "unknown"
            plan = {
                "action": "allow_outreach",
                "summary": "共享层无阻断标签，可进入续费触达计划。",
                "next_steps": [
                    f"按分层 {pool or 'n/a'} 执行触达阶梯：{' → '.join(channels)}",
                    "触达话术回避承诺必赔，仅提示车联服务到期窗口",
                    "可选另次独立跑 crm_lookup（F-UO-019）补齐画像，非本 Skill 联跑",
                ],
                "channels": channels,
                "renew_intent_score": intent,
                "intent_level": intent_level,
                "renew_pool_layer": pool,
            }
            final = (
                f"【触达闸门 · 放行】客户 {customer_id} 允许续费触达。\n"
                f"意向分：{intent if intent is not None else 'n/a'}（{intent_level}）；"
                f"分层：{pool or 'n/a'}\n"
                f"触达阶梯：{' → '.join(channels)}\n"
                f"共享标签：{', '.join(tag_ids) or '（无）'}\n"
                "说明：查数 crm_lookup 为并行可选功能，须另次独立运行。"
            )
            stop = "planned"

        self.registry.call(
            "log_step",
            {
                "step_name": "plan_done",
                "run_id": rid,
                "step_status": "ok",
                "detail": {"stop_reason": stop, "blocked": blocked},
            },
            context=ctx,
        )
        _step(steps, name="plan_done", ok=True, phase="done", detail={"stop_reason": stop})

        return PlanResult(
            ok=True,
            skill_id=skill_id,
            run_id=rid,
            stop_reason=stop,
            customer_id=customer_id,
            vin=vin,
            gate=gate,
            plan=plan,
            final_answer=final,
            steps=steps,
            shared_tag_ids=tag_ids,
            ai_output_ids=ai_ids,
        )


def run_planning(
    skill_id: str,
    user_input: str | dict[str, Any],
    *,
    run_id: str | None = None,
    registry: ToolRegistry | None = None,
) -> PlanResult:
    return PlanningAgent(registry=registry).run(skill_id, user_input, run_id=run_id)
