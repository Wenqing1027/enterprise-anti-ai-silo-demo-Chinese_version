"""运维遥测：健康分 · 四大黄金指标 · 事件/变更 · 分环 · 调用链（Demo 级）。

从 SharedStore run_logs / ai_outputs 推导；样本不足时用可复现合成点填满曲线，
便于作品集演示「指标异常 ↔ 事件关联 ↔ 根因建议」。
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from apps.loops import LOOP_META, PLATFORM_LOOPS, canonicalize, display_name
from apps.skill_loops import control_loop_for_skill
from shared.store.store import SharedStore, default_store
from shared.tools.registry import ToolRegistry, default_registry

_UTC = timezone.utc


def _parse_ts(val: Any) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=_UTC)
    s = str(val).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _infer_loop(run_id: str | None, skill_id: str | None) -> str | None:
    if skill_id:
        loop = control_loop_for_skill(skill_id)
        if loop:
            return loop
    rid = (run_id or "").lower()
    for prefix, loop in (
        ("rag-", "retrieve"),
        ("retrieve-", "retrieve"),
        ("react-", "act"),
        ("act-", "act"),
        ("extract-", "extract"),
        ("ext-", "extract"),
        ("plan-", "plan"),
        ("planning-", "plan"),
    ):
        if rid.startswith(prefix):
            return loop
    return None


def _bucket_key(ts: datetime, minutes: int = 5) -> datetime:
    discard = timedelta(
        minutes=ts.minute % minutes,
        seconds=ts.second,
        microseconds=ts.microsecond,
    )
    return ts - discard


def _synthetic_series(
    *,
    seed: str,
    points: int = 24,
    base: float,
    noise: float,
    dip_at: int | None = None,
    dip_depth: float = 0.25,
) -> list[dict[str, Any]]:
    """可复现伪随机序列（分钟桶），用于 Demo 填满黄金指标。"""
    now = datetime.now(_UTC).replace(second=0, microsecond=0)
    out: list[dict[str, Any]] = []
    for i in range(points):
        ts = now - timedelta(minutes=5 * (points - 1 - i))
        h = hashlib.md5(f"{seed}:{i}".encode()).hexdigest()
        n = (int(h[:8], 16) % 1000) / 1000.0  # 0..1
        v = base + (n - 0.5) * 2 * noise
        if dip_at is not None and abs(i - dip_at) <= 1:
            v = v * (1.0 - dip_depth)
        out.append({"ts": ts.isoformat().replace("+00:00", "Z"), "value": round(max(0.0, v), 3)})
    return out


def _build_run_index(logs: list[Any]) -> dict[str, dict[str, Any]]:
    by_run: dict[str, dict[str, Any]] = {}
    for x in logs:
        rid = getattr(x, "run_id", None)
        if not rid:
            continue
        detail = x.detail if isinstance(getattr(x, "detail", None), dict) else {}
        skill = detail.get("skill_id")
        loop = _infer_loop(rid, skill if isinstance(skill, str) else None)
        row = by_run.setdefault(
            rid,
            {
                "run_id": rid,
                "control_loop": loop,
                "skills": set(),
                "steps": [],
                "errors": 0,
                "blocked": False,
                "stop_reason": None,
                "first_dt": None,
                "last_dt": None,
            },
        )
        if skill:
            row["skills"].add(str(skill))
        if loop and not row["control_loop"]:
            row["control_loop"] = loop
        st = str(getattr(x, "step_status", "")).lower()
        if st in {"error", "fail", "failed"}:
            row["errors"] += 1
        if detail.get("blocked") is True:
            row["blocked"] = True
        if detail.get("stop_reason"):
            row["stop_reason"] = detail.get("stop_reason")
        ts = getattr(x, "step_ts", None)
        ts_dt = ts if isinstance(ts, datetime) else _parse_ts(ts)
        step = {
            "step_name": getattr(x, "step_name", None),
            "step_status": str(getattr(x, "step_status", "")),
            "step_ts": ts_dt.isoformat().replace("+00:00", "Z") if ts_dt else None,
            "detail": detail,
            "control_loop": loop,
        }
        row["steps"].append(step)
        if ts_dt:
            if row["first_dt"] is None or ts_dt < row["first_dt"]:
                row["first_dt"] = ts_dt
            if row["last_dt"] is None or ts_dt > row["last_dt"]:
                row["last_dt"] = ts_dt
    for rid, row in by_run.items():
        row["skills"] = sorted(row["skills"])
        t0, t1 = row.pop("first_dt", None), row.pop("last_dt", None)
        row["first_ts"] = t0.isoformat().replace("+00:00", "Z") if t0 else None
        row["last_ts"] = t1.isoformat().replace("+00:00", "Z") if t1 else None
        if t0 and t1:
            row["duration_ms"] = max(0, int((t1 - t0).total_seconds() * 1000))
        else:
            row["duration_ms"] = 800 + (abs(hash(rid)) % 2200)
        if not row["control_loop"] and row["skills"]:
            row["control_loop"] = control_loop_for_skill(row["skills"][0])
        row["ok"] = row["errors"] == 0
        if row["blocked"] and row["errors"] == 0:
            row["ok"] = True
    return by_run


def build_call_chain(run: dict[str, Any]) -> dict[str, Any]:
    """单次 run 的调用链（入口 → Skill → 步骤节点）。"""
    loop = run.get("control_loop")
    steps = run.get("steps") or []
    nodes: list[dict[str, Any]] = [
        {
            "id": "entry",
            "label": f"入口 · {display_name(loop) if loop else 'run'}",
            "kind": "entry",
        }
    ]
    ids = ["entry"]
    if run.get("skills"):
        nodes.append(
            {
                "id": "skill",
                "label": "Skill · " + ",".join(run["skills"]),
                "kind": "skill",
            }
        )
        ids.append("skill")
    for i, s in enumerate(steps):
        nid = f"s{i}"
        detail = s.get("detail") or {}
        tool = detail.get("tool") or s.get("step_name") or detail.get("phase") or f"step_{i}"
        nodes.append(
            {
                "id": nid,
                "label": str(tool),
                "kind": "step",
                "status": s.get("step_status"),
                "ts": s.get("step_ts"),
                "detail": {
                    k: detail[k]
                    for k in ("tool", "error", "error_code", "latency_ms", "message")
                    if k in detail
                }
                or None,
            }
        )
        ids.append(nid)
    edges = [{"from": a, "to": b} for a, b in zip(ids, ids[1:])]
    severity = "ok"
    if run.get("errors") or run.get("ok") is False:
        severity = "error"
    elif run.get("slow") or (run.get("duration_ms") or 0) >= 5000:
        severity = "slow"
    elif run.get("blocked"):
        severity = "blocked"
    return {
        "run_id": run.get("run_id"),
        "control_loop": loop,
        "duration_ms": run.get("duration_ms"),
        "ok": run.get("ok"),
        "blocked": run.get("blocked"),
        "slow": bool(run.get("slow")),
        "severity": severity,
        "demo": bool(run.get("demo")),
        "nodes": nodes,
        "edges": edges,
    }


# Demo 排障样例：真实 run_logs 全绿时仍要能展示「报错现场 / 慢调用」
DEMO_ERR_RUN_ID = "demo-err-write-govern"
DEMO_SLOW_RUN_ID = "demo-slow-retrieve"


def _fmt_clock(ts: str | None) -> str:
    if not ts:
        return "—"
    return str(ts).replace("T", " ").replace("Z", "")[:16]


def _detect_highlight(
    signals: dict[str, list[dict[str, Any]]],
) -> tuple[str | None, int | None, str]:
    """返回 (highlight_ts, anomaly_idx, reason)。"""
    err_series = signals.get("error_count") or []
    sr_series = signals.get("success_rate") or []
    for i, p in enumerate(err_series):
        if p["value"] >= 2.5:
            return p["ts"], i, "error_spike"
    for i, p in enumerate(sr_series):
        if p["value"] < 85:
            return p["ts"], i, "success_drop"
    if err_series:
        anomaly_idx = max(range(len(err_series)), key=lambda i: err_series[i]["value"])
        if err_series[anomaly_idx]["value"] >= 1.0:
            return err_series[anomaly_idx]["ts"], anomaly_idx, "error_peak"
    return None, None, "none"


def build_demo_incident_runs(*, highlight_ts: str | None = None) -> dict[str, dict[str, Any]]:
    """可复现的故障/慢调用样例（不写盘，仅看板与链路详情用）。"""
    ht = _parse_ts(highlight_ts) or datetime.now(_UTC)
    t_err = ht
    t_slow = ht - timedelta(minutes=2)
    err_run = {
        "run_id": DEMO_ERR_RUN_ID,
        "control_loop": "retrieve",
        "skills": ["policy_kb"],
        "errors": 1,
        "blocked": False,
        "ok": False,
        "slow": False,
        "demo": True,
        "stop_reason": "tool_error",
        "duration_ms": 4210,
        "first_ts": (t_err - timedelta(seconds=4)).isoformat().replace("+00:00", "Z"),
        "last_ts": t_err.isoformat().replace("+00:00", "Z"),
        "steps": [
            {
                "step_name": "rag_start",
                "step_status": "ok",
                "step_ts": (t_err - timedelta(seconds=4)).isoformat().replace("+00:00", "Z"),
                "detail": {"skill_id": "policy_kb", "phase": "start"},
                "control_loop": "retrieve",
            },
            {
                "step_name": "tool_call",
                "step_status": "error",
                "step_ts": (t_err - timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
                "detail": {
                    "tool": "write_govern",
                    "error_code": "TIMEOUT",
                    "error": "connection pool exhausted / downstream timeout",
                    "latency_ms": 3001,
                    "message": "write_govern 调用失败",
                },
                "control_loop": "retrieve",
            },
            {
                "step_name": "rag_done",
                "step_status": "error",
                "step_ts": t_err.isoformat().replace("+00:00", "Z"),
                "detail": {"stop": "tool_error", "tool": "write_govern"},
                "control_loop": "retrieve",
            },
        ],
    }
    slow_run = {
        "run_id": DEMO_SLOW_RUN_ID,
        "control_loop": "retrieve",
        "skills": ["hr_rules"],
        "errors": 0,
        "blocked": False,
        "ok": True,
        "slow": True,
        "demo": True,
        "stop_reason": None,
        "duration_ms": 8120,
        "first_ts": (t_slow - timedelta(seconds=8)).isoformat().replace("+00:00", "Z"),
        "last_ts": t_slow.isoformat().replace("+00:00", "Z"),
        "steps": [
            {
                "step_name": "rag_start",
                "step_status": "ok",
                "step_ts": (t_slow - timedelta(seconds=8)).isoformat().replace("+00:00", "Z"),
                "detail": {"skill_id": "hr_rules", "phase": "start"},
                "control_loop": "retrieve",
            },
            {
                "step_name": "tool_call",
                "step_status": "warn",
                "step_ts": (t_slow - timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
                "detail": {
                    "tool": "write_govern",
                    "latency_ms": 7800,
                    "message": "慢调用：连接池排队",
                },
                "control_loop": "retrieve",
            },
            {
                "step_name": "rag_done",
                "step_status": "ok",
                "step_ts": t_slow.isoformat().replace("+00:00", "Z"),
                "detail": {"stop": "ok", "tool": "write_govern"},
                "control_loop": "retrieve",
            },
        ],
    }
    return {DEMO_ERR_RUN_ID: err_run, DEMO_SLOW_RUN_ID: slow_run}


def _merge_demo_incidents(
    runs: dict[str, dict[str, Any]],
    *,
    highlight_ts: str | None,
) -> dict[str, dict[str, Any]]:
    """真实日志若无 error/slow，注入 Demo 排障样例，避免全绿无法演示。"""
    has_fail = any((r.get("errors") or r.get("ok") is False) for r in runs.values())
    has_slow = any((r.get("duration_ms") or 0) >= 5000 for r in runs.values())
    demo = build_demo_incident_runs(highlight_ts=highlight_ts)
    out = dict(runs)
    if not has_fail:
        out[DEMO_ERR_RUN_ID] = demo[DEMO_ERR_RUN_ID]
    if not has_slow:
        out[DEMO_SLOW_RUN_ID] = demo[DEMO_SLOW_RUN_ID]
    return out


def _sr_delta_around(sr_series: list[dict[str, Any]], anomaly_idx: int | None) -> float | None:
    if anomaly_idx is None or not sr_series:
        return None
    base_vals = [p["value"] for i, p in enumerate(sr_series) if abs(i - anomaly_idx) > 2]
    if not base_vals:
        return None
    base = sum(base_vals) / len(base_vals)
    return round(base - sr_series[anomaly_idx]["value"], 1)


def _golden_from_runs(
    runs: dict[str, dict[str, Any]],
    *,
    loop: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """按 5 分钟桶聚合真实 run；不足则合成补齐。"""
    filtered = [
        r
        for r in runs.values()
        if loop is None or r.get("control_loop") == loop
    ]
    buckets: dict[datetime, dict[str, float]] = defaultdict(
        lambda: {"ok": 0, "total": 0, "rt_sum": 0.0, "errors": 0}
    )
    for r in filtered:
        ts = _parse_ts(r.get("last_ts") or r.get("first_ts"))
        if not ts:
            continue
        b = _bucket_key(ts)
        buckets[b]["total"] += 1
        buckets[b]["rt_sum"] += float(r.get("duration_ms") or 0)
        if r.get("errors"):
            buckets[b]["errors"] += r["errors"]
        if r.get("ok"):
            buckets[b]["ok"] += 1

    points = 24
    seed = f"loop:{loop or 'all'}"
    # 若真实桶太少，整段用合成（并在中段造一个可关联的 dip）
    if len(buckets) < 4:
        dip = 16
        success = _synthetic_series(seed=seed + ":s", points=points, base=0.96, noise=0.03, dip_at=dip, dip_depth=0.18)
        # 成功率百分比
        for p in success:
            p["value"] = round(min(100.0, max(0.0, p["value"] * 100)), 2)
        rt = _synthetic_series(seed=seed + ":rt", points=points, base=420, noise=80, dip_at=dip, dip_depth=-0.55)
        # dip_depth 负值表示升高（故障时 RT 上升）— 修正：手动抬高 dip 附近
        for i, p in enumerate(rt):
            if abs(i - dip) <= 1:
                p["value"] = round(p["value"] * 1.8, 2)
        throughput = _synthetic_series(seed=seed + ":tp", points=points, base=8.5, noise=2.0, dip_at=dip, dip_depth=0.35)
        errors = _synthetic_series(seed=seed + ":e", points=points, base=0.4, noise=0.3, dip_at=dip, dip_depth=-2.5)
        for i, p in enumerate(errors):
            if abs(i - dip) <= 1:
                p["value"] = round(max(p["value"], 3.0 + i % 2), 2)
            else:
                p["value"] = round(max(0.0, p["value"]), 2)
        return {
            "success_rate": success,
            "latency_ms": rt,
            "throughput": throughput,
            "error_count": errors,
        }

    # 真实桶 → 对齐最近 points 个槽
    now = datetime.now(_UTC).replace(second=0, microsecond=0)
    success, rt, tp, err = [], [], [], []
    for i in range(points):
        ts = now - timedelta(minutes=5 * (points - 1 - i))
        b = _bucket_key(ts)
        cell = buckets.get(b)
        if not cell or cell["total"] == 0:
            # 局部合成
            h = hashlib.md5(f"{seed}:{i}".encode()).hexdigest()
            n = (int(h[:6], 16) % 100) / 100.0
            success.append({"ts": ts.isoformat().replace("+00:00", "Z"), "value": round(94 + n * 5, 2)})
            rt.append({"ts": ts.isoformat().replace("+00:00", "Z"), "value": round(300 + n * 200, 2)})
            tp.append({"ts": ts.isoformat().replace("+00:00", "Z"), "value": round(5 + n * 6, 2)})
            err.append({"ts": ts.isoformat().replace("+00:00", "Z"), "value": round(n * 1.5, 2)})
        else:
            rate = 100.0 * cell["ok"] / cell["total"]
            success.append({"ts": b.isoformat().replace("+00:00", "Z"), "value": round(rate, 2)})
            rt.append(
                {
                    "ts": b.isoformat().replace("+00:00", "Z"),
                    "value": round(cell["rt_sum"] / cell["total"], 2),
                }
            )
            tp.append({"ts": b.isoformat().replace("+00:00", "Z"), "value": float(cell["total"])})
            err.append({"ts": b.isoformat().replace("+00:00", "Z"), "value": float(cell["errors"])})
    return {
        "success_rate": success,
        "latency_ms": rt,
        "throughput": tp,
        "error_count": err,
    }


def _health_score(signals: dict[str, list[dict[str, Any]]], *, blocked: int, errors: int) -> dict[str, Any]:
    sr = signals["success_rate"][-1]["value"] if signals["success_rate"] else 95.0
    lat = signals["latency_ms"][-1]["value"] if signals["latency_ms"] else 400.0
    errs = signals["error_count"][-1]["value"] if signals["error_count"] else 0.0
    # 简单加权
    score = sr
    if lat > 800:
        score -= min(15, (lat - 800) / 80)
    if errs > 1:
        score -= min(20, errs * 4)
    if errors:
        score -= min(10, errors * 2)
    score = round(max(0.0, min(100.0, score)), 1)
    level = "excellent" if score >= 95 else "good" if score >= 85 else "degraded" if score >= 70 else "critical"
    return {"score": score, "level": level, "success_rate_now": sr, "latency_ms_now": lat, "errors_now": errs}


def _events_and_rca(
    signals: dict[str, list[dict[str, Any]]],
    runs: dict[str, dict[str, Any]],
    *,
    loop: str | None = None,
    highlight_ts: str | None = None,
    anomaly_idx: int | None = None,
    anomaly_reason: str = "none",
) -> tuple[list[dict[str, Any]], dict[str, Any], str | None]:
    """根据曲线异常 + 变更 + 失败 run 生成「事件/变更」与可追溯根因卡。"""
    err_series = signals.get("error_count") or []
    sr_series = signals.get("success_rate") or []
    if highlight_ts is None:
        highlight_ts, anomaly_idx, anomaly_reason = _detect_highlight(signals)

    sr_drop = _sr_delta_around(sr_series, anomaly_idx)
    err_at = None
    if anomaly_idx is not None and err_series and anomaly_idx < len(err_series):
        err_at = err_series[anomaly_idx]["value"]

    impact_loop = loop or "retrieve"
    impact_effect = (
        f"导致 {display_name(impact_loop)} 环成功率下降约 {abs(sr_drop)}%"
        if sr_drop and sr_drop > 0
        else f"导致 {display_name(impact_loop)} 环错误数抬升"
        + (f"（峰值 {err_at}）" if err_at is not None else "")
    )

    now = datetime.now(_UTC)
    deploy_ts = (
        ((_parse_ts(highlight_ts) or now) - timedelta(minutes=3)).isoformat().replace("+00:00", "Z")
        if highlight_ts
        else (now - timedelta(minutes=95)).isoformat().replace("+00:00", "Z")
    )
    ledger_ts = (now - timedelta(minutes=95)).isoformat().replace("+00:00", "Z")

    events: list[dict[str, Any]] = [
        {
            "ts": ledger_ts,
            "kind": "deploy",
            "title": "平台工具台账 v2 发布",
            "detail": "write_govern 类工具白名单调整",
            "loop": loop,
            "correlate": bool(highlight_ts),
            "impact_scope": "write_govern",
            "impact": impact_effect if highlight_ts else "影响范围待观察",
            "impact_level": "warn" if highlight_ts else "info",
        },
        {
            "ts": (now - timedelta(minutes=48)).isoformat().replace("+00:00", "Z"),
            "kind": "config",
            "title": "Skill allowlist 热更新",
            "detail": "fill_ticket / renewal_plan consumer_allow",
            "loop": loop,
            "correlate": False,
            "impact_scope": "renewal_plan",
            "impact": "Plan 环闸门策略收紧（与本次指标异常弱相关）",
            "impact_level": "info",
        },
    ]
    if highlight_ts:
        events.append(
            {
                "ts": deploy_ts,
                "kind": "deploy",
                "title": "控制环热更新（疑似）",
                "detail": f"{display_name(loop) if loop else '平台'} 配置推送 · 指标约 3 分钟后波动",
                "loop": loop or impact_loop,
                "correlate": True,
                "impact_scope": "write_govern",
                "impact": impact_effect,
                "impact_level": "warn",
            }
        )
        events.append(
            {
                "ts": highlight_ts,
                "kind": "alert",
                "title": "告警：变更后指标变差",
                "detail": (
                    f"关联变更「平台工具台账 v2 / 控制环热更新」后，"
                    f"{impact_effect}；判定为告警而非单纯变更记录。"
                ),
                "loop": loop or impact_loop,
                "correlate": True,
                "impact_scope": "write_govern",
                "impact": impact_effect,
                "impact_level": "critical",
            }
        )

    for r in sorted(runs.values(), key=lambda x: x.get("last_ts") or "", reverse=True)[:10]:
        if loop and r.get("control_loop") != loop:
            continue
        if r.get("errors") or r.get("ok") is False:
            tool = "write_govern"
            for s in r.get("steps") or []:
                d = s.get("detail") or {}
                if d.get("tool"):
                    tool = str(d["tool"])
                    break
            events.append(
                {
                    "ts": r.get("last_ts"),
                    "kind": "error",
                    "title": f"报错现场 · {r['run_id']}",
                    "detail": f"tool={tool} errors={r.get('errors')} stop={r.get('stop_reason')}",
                    "loop": r.get("control_loop"),
                    "run_id": r["run_id"],
                    "correlate": True,
                    "impact_scope": tool,
                    "impact": f"{tool} 调用失败，拉低 {display_name(r.get('control_loop') or impact_loop)} 成功率",
                    "impact_level": "critical",
                }
            )
        elif r.get("slow") or (r.get("duration_ms") or 0) >= 5000:
            events.append(
                {
                    "ts": r.get("last_ts"),
                    "kind": "warn",
                    "title": f"慢调用 · {r['run_id']}",
                    "detail": f"duration_ms={r.get('duration_ms')}",
                    "loop": r.get("control_loop"),
                    "run_id": r["run_id"],
                    "correlate": True,
                    "impact_scope": "write_govern",
                    "impact": f"RT 抬升至 {r.get('duration_ms')} ms（连接池排队）",
                    "impact_level": "warn",
                }
            )
        elif r.get("blocked"):
            events.append(
                {
                    "ts": r.get("last_ts"),
                    "kind": "gate",
                    "title": f"闸门阻断 · {r['run_id']}",
                    "detail": f"skills={','.join(r.get('skills') or [])} stop={r.get('stop_reason')}",
                    "loop": r.get("control_loop"),
                    "run_id": r["run_id"],
                    "correlate": False,
                    "impact_scope": ",".join(r.get("skills") or []) or "gate",
                    "impact": "策略闸门命中（治理正常，非本次指标主因）",
                    "impact_level": "info",
                }
            )

    events.sort(key=lambda e: e.get("ts") or "", reverse=True)

    # —— 根因：用已有数据做 if-else 证据链（坦诚标注规则引擎，非黑盒 ML）——
    fail_runs = [
        r
        for r in runs.values()
        if (not loop or r.get("control_loop") == loop)
        and (r.get("errors") or r.get("ok") is False)
    ]
    slow_runs = [
        r
        for r in runs.values()
        if (not loop or r.get("control_loop") == loop)
        and (r.get("slow") or (r.get("duration_ms") or 0) >= 5000)
    ]
    related = [r["run_id"] for r in (fail_runs + slow_runs)][:5]
    if not related:
        related = [
            r["run_id"]
            for r in runs.values()
            if (not loop or r.get("control_loop") == loop) and r.get("blocked")
        ][:3]

    evidence: list[str] = []
    if highlight_ts:
        evidence.append(
            f"指标：{_fmt_clock(highlight_ts)} 出现异常"
            + (f"（错误峰值 {err_at}）" if err_at is not None else "")
            + (f"，成功率约降 {abs(sr_drop)}%" if sr_drop and sr_drop > 0 else "")
            + f"；检测规则={anomaly_reason}"
        )
    evidence.append(f"变更：平台工具台账 v2 / 控制环热更新 · {_fmt_clock(deploy_ts)} · 影响范围 write_govern")

    tool_hit = None
    for r in fail_runs:
        for s in r.get("steps") or []:
            d = s.get("detail") or {}
            if d.get("tool") and str(s.get("step_status", "")).lower() in {"error", "fail", "failed"}:
                tool_hit = str(d["tool"])
                evidence.append(
                    f"报错：run `{r['run_id']}` · 工具 {tool_hit}"
                    + (f" · {d.get('error_code')}" if d.get("error_code") else "")
                    + (f" · {d.get('error')}" if d.get("error") else "")
                )
                break
        if tool_hit:
            break
    if not tool_hit and slow_runs:
        r0 = slow_runs[0]
        evidence.append(f"慢调用：run `{r0['run_id']}` · RT {r0.get('duration_ms')} ms（write_govern 排队）")
        tool_hit = "write_govern"

    if highlight_ts and tool_hit:
        chain = (
            f"根因推断：检测到 {tool_hit} 工具错误/慢调用上升"
            f" → 关联到工具白名单变更事件（时间戳 {_fmt_clock(deploy_ts)}）"
            f" → 建议检查该工具连接池配置与下游超时。"
        )
        rca = {
            "title": "根因分析",
            "mode": "rule_engine",
            "summary": chain,
            "suspect": f"{tool_hit} 在变更后出现 TIMEOUT / 连接池耗尽（由指标异常 + 变更时间窗 + 报错 run 共同推出）",
            "suggestion": f"检查 {tool_hit} 连接池与超时；必要时回滚台账 v2；重试失败 run。",
            "confidence": 0.82 if fail_runs else 0.7,
            "highlight_ts": highlight_ts,
            "related_run_ids": related,
            "evidence": evidence,
            "log_query": {"q": tool_hit, "status": "error", "run_ids": related},
        }
    elif highlight_ts:
        chain = (
            f"根因推断：检测到黄金指标异常（{_fmt_clock(highlight_ts)}）"
            f" → 时间窗内存在 write_govern 相关变更"
            f" → 建议打开错误日志核对工具调用。"
        )
        rca = {
            "title": "根因分析",
            "mode": "rule_engine",
            "summary": chain,
            "suspect": "变更后指标变差，待用错误日志确认工具侧失败模式",
            "suggestion": "打开相关错误日志；对照变更单与失败 run。",
            "confidence": 0.62,
            "highlight_ts": highlight_ts,
            "related_run_ids": related,
            "evidence": evidence,
            "log_query": {"q": "write_govern", "status": "error", "run_ids": related},
        }
    else:
        rca = {
            "title": "根因分析",
            "mode": "rule_engine",
            "summary": "当前四大黄金指标未触发异常规则，无自动根因。",
            "suspect": "无显著异常",
            "suggestion": "保持巡检；可在业务墙跑 Story 产生更多 run。",
            "confidence": 0.9,
            "highlight_ts": None,
            "related_run_ids": [],
            "evidence": ["规则：error_count≥2.5 或 success_rate<85 才触发关联分析"],
            "log_query": {"q": None, "status": "error", "run_ids": []},
        }
    return events[:16], rca, highlight_ts


def build_ops_dashboard(
    *,
    loop: str | None = None,
    store: SharedStore | None = None,
    registry: ToolRegistry | None = None,
) -> dict[str, Any]:
    store = store or default_store
    registry = registry or default_registry
    loop = canonicalize(loop) if loop else None
    if loop and loop not in PLATFORM_LOOPS:
        loop = None

    logs = store.list_run_logs()
    runs = _build_run_index(logs)
    signals = _golden_from_runs(runs, loop=loop)
    highlight_ts, anomaly_idx, anomaly_reason = _detect_highlight(signals)
    runs = _merge_demo_incidents(runs, highlight_ts=highlight_ts)

    err_steps = sum(
        1 for x in logs if str(getattr(x, "step_status", "")).lower() in {"error", "fail", "failed"}
    )
    err_steps += sum(int(r.get("errors") or 0) for r in runs.values() if r.get("demo"))
    blocked = sum(
        1
        for r in runs.values()
        if r.get("blocked") and (loop is None or r.get("control_loop") == loop)
    )
    health = _health_score(signals, blocked=blocked, errors=err_steps)
    events, rca, highlight_ts = _events_and_rca(
        signals,
        runs,
        loop=loop,
        highlight_ts=highlight_ts,
        anomaly_idx=anomaly_idx,
        anomaly_reason=anomaly_reason,
    )

    def _run_rank(r: dict[str, Any]) -> tuple:
        # 报错 / 慢调用优先展示，便于演示排障
        sev = 0
        if r.get("errors") or r.get("ok") is False:
            sev = 0
        elif r.get("slow") or (r.get("duration_ms") or 0) >= 5000:
            sev = 1
        elif r.get("blocked"):
            sev = 2
        else:
            sev = 3
        return (sev, -( _parse_ts(r.get("last_ts")).timestamp() if _parse_ts(r.get("last_ts")) else 0))

    run_list = [
        {
            "run_id": r["run_id"],
            "control_loop": r.get("control_loop"),
            "skills": r.get("skills"),
            "steps": len(r.get("steps") or []),
            "errors": r.get("errors"),
            "blocked": r.get("blocked"),
            "ok": r.get("ok"),
            "slow": bool(r.get("slow") or (r.get("duration_ms") or 0) >= 5000),
            "demo": bool(r.get("demo")),
            "duration_ms": r.get("duration_ms"),
            "last_ts": r.get("last_ts"),
            "stop_reason": r.get("stop_reason"),
        }
        for r in sorted(
            [x for x in runs.values() if loop is None or x.get("control_loop") == loop],
            key=_run_rank,
        )
    ][:20]

    chains = [build_call_chain(runs[r["run_id"]]) for r in run_list[:6] if r["run_id"] in runs]

    loop_cards = []
    for lid in PLATFORM_LOOPS:
        subset = [r for r in runs.values() if r.get("control_loop") == lid]
        ok_n = sum(1 for r in subset if r.get("ok") and not r.get("errors"))
        loop_cards.append(
            {
                "control_loop": lid,
                "name": LOOP_META[lid]["name"],
                "runs": len(subset),
                "success_rate": round(100.0 * ok_n / len(subset), 1) if subset else None,
                "status": LOOP_META[lid]["status"],
            }
        )

    tools = registry.tool_class_summary()
    return {
        "ok": True,
        "purpose": "troubleshooting_dashboard",
        "scope": loop or "platform",
        "control_loop": loop,
        "health": health,
        "golden_signals": {
            "success_rate": {"label": "成功率 %", "unit": "%", "points": signals["success_rate"]},
            "latency_ms": {"label": "RT 响应时间", "unit": "ms", "points": signals["latency_ms"]},
            "throughput": {"label": "吞吐量", "unit": "runs/桶", "points": signals["throughput"]},
            "error_count": {"label": "错误数", "unit": "count", "points": signals["error_count"]},
        },
        "events": events,
        "highlight_ts": highlight_ts,
        "root_cause": rca,
        "runs": run_list,
        "call_chains": chains,
        "loop_cards": loop_cards,
        "tool_counts": tools.get("counts") or {},
        "stats": store.stats(),
    }


def build_ops_run_trace(run_id: str, *, store: SharedStore | None = None) -> dict[str, Any]:
    store = store or default_store
    demo = build_demo_incident_runs()
    if run_id in demo:
        run = demo[run_id]
        return {
            "run_id": run_id,
            "found": True,
            "summary": {
                "control_loop": run.get("control_loop"),
                "skills": run.get("skills"),
                "duration_ms": run.get("duration_ms"),
                "ok": run.get("ok"),
                "blocked": run.get("blocked"),
                "slow": run.get("slow"),
                "stop_reason": run.get("stop_reason"),
                "demo": True,
            },
            "call_chain": build_call_chain(run),
            "steps": run.get("steps") or [],
            "ai_outputs": [],
        }
    logs = store.list_run_logs(run_id=run_id)
    runs = _build_run_index(logs)
    run = runs.get(run_id)
    if not run:
        return {"run_id": run_id, "found": False, "call_chain": None, "steps": [], "ai_outputs": []}
    outputs = store.read_ai_outputs(run_id=run_id, limit=50)
    return {
        "run_id": run_id,
        "found": True,
        "summary": {
            "control_loop": run.get("control_loop"),
            "skills": run.get("skills"),
            "duration_ms": run.get("duration_ms"),
            "ok": run.get("ok"),
            "blocked": run.get("blocked"),
            "stop_reason": run.get("stop_reason"),
        },
        "call_chain": build_call_chain(run),
        "steps": run.get("steps") or [],
        "ai_outputs": [
            o.model_dump(mode="json") if hasattr(o, "model_dump") else o for o in outputs
        ],
    }
