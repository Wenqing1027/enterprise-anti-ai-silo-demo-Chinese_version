"""青枢出行 · 业务平台 + 嵌入式运维 API（模块五）。"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_ENV = ROOT / ".env"
if _ENV.is_file():
    load_dotenv(_ENV, override=True)
else:
    load_dotenv(override=False)

# 尽早剥离 IDE 注入代理，避免后续 OpenAI/httpx 走坏掉的本地代理
if (os.getenv("DEEPSEEK_TRUST_ENV") or "").strip().lower() not in {"1", "true", "yes"}:
    for _k in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "SOCKS_PROXY",
        "SOCKS5_PROXY",
        "socks_proxy",
        "socks5_proxy",
    ):
        os.environ.pop(_k, None)

from agents.extraction.agent import run_extraction
from agents.planning.agent import run_planning
from agents.rag.agent import run_rag
from agents.react.agent import run_react
from agents.react.skill_loader import list_skill_ids
from apps.skill_dispatch import load_skill_public, peek_skill_kind
from apps.catalog import (
    get_agent_type,
    get_department,
    get_feature,
    get_flow,
    get_flows_by_department,
    list_agent_types,
    list_departments,
    list_features,
    list_flows,
    list_roles,
    public_view_from_feature,
    resolve_department_for_skill,
)
from apps.loops import PLATFORM_LOOPS, LOOP_META, canonicalize
from apps.loops import meta_payload as loops_meta_payload
from apps.loops import same_loop, to_legacy
from apps.run_result import RUN_RESULT_VERSION, wrap_run_result
from shared.store.store import default_store
from shared.tools.governance import TOOL_CLASSES, meta_payload as tools_meta_payload
from shared.tools.registry import default_registry

_KIND_TO_LOOP = {
    "react": "act",
    "extraction": "extract",
    "rag": "retrieve",
    "planning": "plan",
}


def _decorate_and_wrap(
    raw: dict[str, Any],
    *,
    control_loop: str,
    body_feature_id: str | None,
    body_department_id: str | None,
    feature: dict[str, Any] | None,
    view: dict[str, Any] | None,
    default_layout: str = "generic",
    extra_extensions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """路由层装饰字段 + 统一 RunResult。"""
    feature_id = body_feature_id or (feature["feature_id"] if feature else None)
    department_id = (
        (view or {}).get("department_id")
        or body_department_id
        or (feature or {}).get("department_id")
    )
    layout = (view or {}).get("layout") or (feature or {}).get("layout") or default_layout
    tone_label = (view or {}).get("tone_label") or (feature or {}).get("tone_label")
    department_name = (view or {}).get("name") or (feature or {}).get("department_name")
    return wrap_run_result(
        raw,
        control_loop=control_loop,
        feature_id=feature_id,
        department_id=department_id,
        layout=layout,
        tone_label=tone_label,
        department_name=department_name,
        extra_extensions=extra_extensions,
    )

UI_DIR = Path(__file__).resolve().parent / "ui"
API_VERSION = "2026.08.07"
PRODUCT = "Qingshu Mobility · Anti-AI-Silo"


def _cors_origins() -> list[str]:
    raw = (os.getenv("DEMO_CORS_ORIGINS") or "*").strip()
    if raw == "*":
        return ["*"]
    return [x.strip() for x in raw.split(",") if x.strip()]


app = FastAPI(
    title=PRODUCT,
    version=API_VERSION,
    description=(
        "业务平台（部门×角色×功能聚合）+ 运维控制台（按 Agent 类型分治，可 iframe 嵌入）。"
        "详见 docs/react/05-模块五-界面原则-集成API.md。"
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if UI_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(UI_DIR)), name="static")


def _check_api_key(x_api_key: str | None) -> None:
    expected = (os.getenv("DEMO_API_KEY") or "").strip()
    if not expected:
        return
    if not x_api_key or x_api_key.strip() != expected:
        raise HTTPException(status_code=401, detail="invalid or missing X-Api-Key")


def _ui(name: str) -> Path:
    path = UI_DIR / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"ui not found: {name}")
    return path


def _demo_video_local_path() -> Path:
    return UI_DIR / "media" / "demo-walkthrough.mp4"


def _fetch_demo_video_from_private_github() -> Path | None:
    """从私有仓库拉取讲解视频到本地缓存（不进入公开 Git）。"""
    token = (os.getenv("GH_MEDIA_TOKEN") or os.getenv("GITHUB_TOKEN") or "").strip()
    if not token:
        return None
    dest = _demo_video_local_path()
    if dest.is_file() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    repo = (os.getenv("DEMO_VIDEO_REPO") or "Wenqing1027/qingshu-demo-media-private").strip()
    path_in_repo = (os.getenv("DEMO_VIDEO_PATH") or "demo-walkthrough.mp4").strip()
    url = f"https://api.github.com/repos/{repo}/contents/{path_in_repo}"
    try:
        import urllib.request

        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.raw",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "qingshu-demo",
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
            data = resp.read()
        if not data:
            return None
        dest.write_bytes(data)
        return dest
    except Exception:  # noqa: BLE001
        return None


@app.get("/media/demo-walkthrough.mp4")
def demo_walkthrough_video() -> FileResponse:
    """讲解视频：优先本地；否则用 GH_MEDIA_TOKEN 从私有库拉取。"""
    path = _demo_video_local_path()
    if not (path.is_file() and path.stat().st_size > 0):
        path = _fetch_demo_video_from_private_github() or path
    if not (path.is_file() and path.stat().st_size > 0):
        raise HTTPException(
            status_code=404,
            detail="demo video missing: set GH_MEDIA_TOKEN on Render to fetch from private media repo",
        )
    return FileResponse(
        path,
        media_type="video/mp4",
        filename="青枢出行-Demo讲解.mp4",
    )

class ReactRunOptions(BaseModel):
    return_steps: bool = True


class ReactRunRequest(BaseModel):
    feature_id: str | None = Field(
        default=None,
        description="业务功能 ID；若提供则必须 demo_ready",
    )
    department_id: str | None = None
    skill_id: str | None = None
    input: dict[str, Any] | str = Field(default_factory=dict)
    run_id: str | None = None
    options: ReactRunOptions = Field(default_factory=ReactRunOptions)


class ExtractionRunOptions(BaseModel):
    return_steps: bool = True
    write_output: bool = True


class ExtractionRunRequest(BaseModel):
    feature_id: str | None = None
    department_id: str | None = None
    skill_id: str | None = None
    input: dict[str, Any] | str = Field(default_factory=dict)
    run_id: str | None = None
    options: ExtractionRunOptions = Field(default_factory=ExtractionRunOptions)


class RagRunOptions(BaseModel):
    return_steps: bool = True


class RagRunRequest(BaseModel):
    feature_id: str | None = None
    department_id: str | None = None
    skill_id: str | None = None
    input: dict[str, Any] | str = Field(default_factory=dict)
    run_id: str | None = None
    options: RagRunOptions = Field(default_factory=RagRunOptions)


class PlanningRunOptions(BaseModel):
    return_steps: bool = True


class PlanningRunRequest(BaseModel):
    feature_id: str | None = None
    department_id: str | None = None
    skill_id: str | None = None
    input: dict[str, Any] | str = Field(default_factory=dict)
    run_id: str | None = None
    options: PlanningRunOptions = Field(default_factory=PlanningRunOptions)


class UnifiedRunOptions(BaseModel):
    return_steps: bool = True


class UnifiedRunRequest(BaseModel):
    """统一运行入口：用 control_loop（或历史 agent_type）分发到各环专用 handler。"""

    control_loop: str | None = Field(
        default=None,
        description="规范环 retrieve|act|extract|plan；可省略，由 feature/skill 推断",
    )
    agent_type: str | None = Field(
        default=None,
        description="历史别名或规范名，与 control_loop 等价；二者皆空则从 feature/skill 推断",
    )
    feature_id: str | None = None
    department_id: str | None = None
    skill_id: str | None = None
    input: dict[str, Any] | str = Field(default_factory=dict)
    run_id: str | None = None
    options: UnifiedRunOptions = Field(default_factory=UnifiedRunOptions)


class AiOutputsReadRequest(BaseModel):
    consumer_skill: str | None = None
    producer_skill: str | None = None
    customer_id: str | None = None
    vin: str | None = None
    limit: int = 20


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "product": PRODUCT, "version": API_VERSION}


@app.get("/v1/meta")
def meta() -> dict[str, Any]:
    loops = loops_meta_payload()
    tools = tools_meta_payload()
    return {
        "product": PRODUCT,
        "version": API_VERSION,
        **loops,
        **tools,
        # 兼容旧客户端：仍返回历史名列表（与 agent_types_ready 规范名并存）
        "agent_types_ready_legacy": [
            to_legacy(x) for x in loops["agent_types_ready"] if to_legacy(x)
        ],
        "business_ui": "/business?department=service",
        "ops_ui": "/ops",
        "ops_embed": "/ops/embed",
        "embed": {
            "business": "/business?department=service",
            "ops_iframe": "/ops/embed",
            "primary_api": "POST /v1/react/runs",
            "extraction_api": "POST /v1/extraction/runs",
            "rag_api": "POST /v1/rag/runs",
            "planning_api": "POST /v1/planning/runs",
            "unified_runs_api": "POST /v1/runs",
            "ops_overview_api": "GET /v1/ops/overview",
            "ops_logs_api": "GET /v1/ops/logs",
            "tools_api": "GET /v1/tools",
            "flows_api": "GET /v1/flows",
            "openapi": "/docs",
            "auth_note": "可选 X-Api-Key（仅当设置 DEMO_API_KEY）；非 SSO/RBAC",
        },
        "runs_api": {
            "unified": "/v1/runs",
            "by_loop": {lid: LOOP_META[lid]["api_path"] for lid in PLATFORM_LOOPS},
        },
        "run_result_version": RUN_RESULT_VERSION,
        "run_result": {
            "common": [
                "run_id",
                "control_loop",
                "skill_id",
                "ok",
                "final_text",
                "steps",
                "ai_output_ids",
                "error",
            ],
            "extensions_by_loop": {
                "extract": ["payload"],
                "retrieve": ["citations"],
                "plan": ["gate.blocked", "gate.reason", "gate.tag_ids"],
                "act": [],
            },
            "bag": "extensions",
            "compat_alias": {"final_answer": "final_text"},
        },
        "brand": "青枢出行（Qingshu Mobility）",
    }


@app.get("/v1/departments")
def departments(
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    _check_api_key(x_api_key)
    rows = list_departments()
    return {"departments": rows, "count": len(rows)}


@app.get("/v1/departments/{department_id}")
def department_one(
    department_id: str,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    _check_api_key(x_api_key)
    row = get_department(department_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"unknown department: {department_id}")
    return row


@app.get("/v1/departments/{department_id}/roles")
def department_roles(
    department_id: str,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    _check_api_key(x_api_key)
    if not get_department(department_id):
        raise HTTPException(status_code=404, detail=f"unknown department: {department_id}")
    rows = list_roles(department_id)
    return {"department_id": department_id, "roles": rows, "count": len(rows)}


@app.get("/v1/flows")
def flows_list(
    demo_ready: bool | None = Query(default=None),
    department_id: str | None = Query(default=None),
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    """部门内功能关系说明书（Planning 机读源）。只读契约，非运行时联跑引擎。"""
    _check_api_key(x_api_key)
    rows = list_flows(demo_ready=demo_ready)
    if department_id:
        rows = [f for f in rows if f.get("department_id") == department_id]
    return {"flows": rows, "count": len(rows)}


@app.get("/v1/flows/{flow_id}")
def flow_one(
    flow_id: str,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    _check_api_key(x_api_key)
    row = get_flow(flow_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"unknown flow: {flow_id}")
    return row


@app.get("/v1/departments/{department_id}/flows")
def department_flows(
    department_id: str,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    _check_api_key(x_api_key)
    if not get_department(department_id):
        raise HTTPException(status_code=404, detail=f"unknown department: {department_id}")
    rows = get_flows_by_department(department_id)
    return {"department_id": department_id, "flows": rows, "count": len(rows)}


@app.get("/v1/features")
def features(
    department_id: str | None = None,
    role_id: str | None = None,
    agent_type: str | None = None,
    demo_only: bool = False,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    _check_api_key(x_api_key)
    rows = list_features(
        department_id=department_id,
        role_id=role_id,
        agent_type=agent_type,
        demo_only=demo_only,
    )
    return {"features": rows, "count": len(rows)}


@app.get("/v1/features/{feature_id}")
def feature_one(
    feature_id: str,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    _check_api_key(x_api_key)
    row = get_feature(feature_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"unknown feature: {feature_id}")
    return row


@app.get("/v1/agent-types")
def agent_types(
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    _check_api_key(x_api_key)
    rows = list_agent_types()
    return {
        "agent_types": rows,
        "count": len(rows),
        "control_loops": ["retrieve", "act", "extract", "plan"],
        "agent_type_aliases": {
            "rag": "retrieve",
            "react": "act",
            "extraction": "extract",
            "planning": "plan",
        },
    }


@app.get("/v1/agent-types/{agent_type}")
def agent_type_one(
    agent_type: str,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    _check_api_key(x_api_key)
    row = get_agent_type(agent_type)
    if not row:
        raise HTTPException(status_code=404, detail=f"unknown agent_type: {agent_type}")
    return row


@app.get("/v1/skills")
def skills(
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    _check_api_key(x_api_key)
    items = []
    for sid in list_skill_ids():
        try:
            pub = load_skill_public(sid)
        except Exception as exc:  # noqa: BLE001
            items.append({"skill_id": sid, "error": str(exc)})
            continue
        dept = resolve_department_for_skill(sid)
        items.append(
            {
                "skill_id": pub["skill_id"],
                "control_loop": pub.get("control_loop"),
                "agent_kind": pub.get("agent_kind"),
                "agent_type_legacy": pub.get("agent_type_legacy"),
                "department": pub.get("department"),
                "department_id": dept["department_id"] if dept else None,
                "goal": pub.get("goal"),
                "tone_label": pub.get("tone_label"),
                "layout": dept["layout"] if dept else None,
                "allowed_tools": pub.get("allowed_tools") or [],
                "payload_schema": pub.get("payload_schema"),
                "success_when": pub.get("success_when"),
            }
        )
    return {"skills": items, "count": len(items)}


@app.get("/v1/skills/{skill_id}")
def skill_one(
    skill_id: str,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    _check_api_key(x_api_key)
    try:
        pub = load_skill_public(skill_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    dept = resolve_department_for_skill(skill_id)
    return {
        **pub,
        "department_view": dept,
    }


@app.post("/v1/react/runs")
def react_run(
    body: ReactRunRequest,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    _check_api_key(x_api_key)

    feature = None
    view: dict[str, Any] | None = None
    skill_id = body.skill_id

    if body.feature_id:
        feature = get_feature(body.feature_id)
        if not feature:
            raise HTTPException(status_code=404, detail=f"unknown feature: {body.feature_id}")
        if not feature.get("demo_ready"):
            raise HTTPException(
                status_code=403,
                detail=(
                    f"feature {body.feature_id} 为板块展示（一期未开放），"
                    "不可直接运行。请选择 demo_ready 功能。"
                ),
            )
        if not feature.get("skill_id"):
            raise HTTPException(
                status_code=403,
                detail=f"feature {body.feature_id} 尚未挂载 skill",
            )
        skill_id = feature["skill_id"]
        view = public_view_from_feature(feature)

    if not skill_id:
        raise HTTPException(
            status_code=400,
            detail="feature_id or skill_id required",
        )

    try:
        if peek_skill_kind(skill_id) != "react":
            # Demo 容错：旧前端误打 ReAct 入口时，自动转发到 Extraction
            return extraction_run(body=ExtractionRunRequest(
                feature_id=body.feature_id,
                department_id=body.department_id,
                skill_id=skill_id,
                input=body.input,
                run_id=body.run_id,
                options=ExtractionRunOptions(return_steps=body.options.return_steps),
            ), x_api_key=x_api_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if view is None:
        view = resolve_department_for_skill(skill_id)

    user_input: dict[str, Any] | str = body.input

    try:
        result = run_react(skill_id, user_input, run_id=body.run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"react failed: {exc}") from exc

    payload = result.to_dict()
    if not body.options.return_steps:
        payload["steps"] = []
    return _decorate_and_wrap(
        payload,
        control_loop="act",
        body_feature_id=body.feature_id,
        body_department_id=body.department_id,
        feature=feature,
        view=view,
        default_layout="generic",
        extra_extensions={"api_path": "/v1/react/runs", "agent_type_legacy": "react"},
    )


@app.post("/v1/extraction/runs")
def extraction_run(
    body: ExtractionRunRequest,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    _check_api_key(x_api_key)

    feature = None
    view: dict[str, Any] | None = None
    skill_id = body.skill_id

    if body.feature_id:
        feature = get_feature(body.feature_id)
        if not feature:
            raise HTTPException(status_code=404, detail=f"unknown feature: {body.feature_id}")
        if not feature.get("demo_ready"):
            raise HTTPException(
                status_code=403,
                detail=(
                    f"feature {body.feature_id} 为板块展示（一期未开放），"
                    "不可直接运行。"
                ),
            )
        if not same_loop(feature.get("agent_type"), "extract"):
            raise HTTPException(
                status_code=400,
                detail=f"feature {body.feature_id} 不是 extract 类型",
            )
        if not feature.get("skill_id"):
            raise HTTPException(
                status_code=403,
                detail=f"feature {body.feature_id} 尚未挂载 skill",
            )
        skill_id = feature["skill_id"]
        view = public_view_from_feature(feature)

    if not skill_id:
        raise HTTPException(
            status_code=400,
            detail="feature_id or skill_id required",
        )

    try:
        if peek_skill_kind(skill_id) != "extraction":
            raise HTTPException(
                status_code=400,
                detail=f"skill {skill_id} 不是 Extraction Skill",
            )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if view is None:
        view = resolve_department_for_skill(skill_id)

    try:
        result = run_extraction(
            skill_id,
            body.input,
            run_id=body.run_id,
            write_output=body.options.write_output,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"extraction failed: {exc}") from exc

    payload = result.to_dict()
    if not body.options.return_steps:
        payload["steps"] = []
    return _decorate_and_wrap(
        payload,
        control_loop="extract",
        body_feature_id=body.feature_id,
        body_department_id=body.department_id,
        feature=feature,
        view=view,
        default_layout="extract",
        extra_extensions={
            "api_path": "/v1/extraction/runs",
            "agent_type_legacy": "extraction",
        },
    )


@app.post("/v1/rag/runs")
def rag_run(
    body: RagRunRequest,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    _check_api_key(x_api_key)

    feature = None
    view: dict[str, Any] | None = None
    skill_id = body.skill_id

    if body.feature_id:
        feature = get_feature(body.feature_id)
        if not feature:
            raise HTTPException(status_code=404, detail=f"unknown feature: {body.feature_id}")
        if not feature.get("demo_ready"):
            raise HTTPException(
                status_code=403,
                detail=(
                    f"feature {body.feature_id} 为板块展示（一期未开放），"
                    "不可直接运行。"
                ),
            )
        if not same_loop(feature.get("agent_type"), "retrieve"):
            raise HTTPException(
                status_code=400,
                detail=f"feature {body.feature_id} 不是 retrieve 类型",
            )
        if not feature.get("skill_id"):
            raise HTTPException(
                status_code=403,
                detail=f"feature {body.feature_id} 尚未挂载 skill",
            )
        skill_id = feature["skill_id"]
        view = public_view_from_feature(feature)

    if not skill_id:
        raise HTTPException(
            status_code=400,
            detail="feature_id or skill_id required",
        )

    try:
        if peek_skill_kind(skill_id) != "rag":
            raise HTTPException(
                status_code=400,
                detail=f"skill {skill_id} 不是 RAG Skill",
            )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if view is None:
        view = resolve_department_for_skill(skill_id)

    try:
        result = run_rag(skill_id, body.input, run_id=body.run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"rag failed: {exc}") from exc

    payload = result.to_dict()
    if not body.options.return_steps:
        payload["steps"] = []
    return _decorate_and_wrap(
        payload,
        control_loop="retrieve",
        body_feature_id=body.feature_id,
        body_department_id=body.department_id,
        feature=feature,
        view=view,
        default_layout="rag",
        extra_extensions={"api_path": "/v1/rag/runs", "agent_type_legacy": "rag"},
    )


@app.post("/v1/planning/runs")
def planning_run(
    body: PlanningRunRequest,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    """Plan 环：读共享 → 闸门 → 结构化计划/阻断（另次独立运行）。"""
    _check_api_key(x_api_key)

    feature = None
    view: dict[str, Any] | None = None
    skill_id = body.skill_id

    if body.feature_id:
        feature = get_feature(body.feature_id)
        if not feature:
            raise HTTPException(status_code=404, detail=f"unknown feature: {body.feature_id}")
        if not feature.get("demo_ready"):
            raise HTTPException(
                status_code=403,
                detail=(
                    f"feature {body.feature_id} 为板块展示（一期未开放），"
                    "不可直接运行。"
                ),
            )
        if not same_loop(feature.get("agent_type"), "plan"):
            raise HTTPException(
                status_code=400,
                detail=f"feature {body.feature_id} 不是 plan 类型",
            )
        if not feature.get("skill_id"):
            raise HTTPException(
                status_code=403,
                detail=f"feature {body.feature_id} 尚未挂载 skill",
            )
        skill_id = feature["skill_id"]
        view = public_view_from_feature(feature)

    if not skill_id:
        raise HTTPException(
            status_code=400,
            detail="feature_id or skill_id required",
        )

    try:
        if peek_skill_kind(skill_id) != "planning":
            raise HTTPException(
                status_code=400,
                detail=f"skill {skill_id} 不是 Planning Skill",
            )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if view is None:
        view = resolve_department_for_skill(skill_id)

    try:
        result = run_planning(skill_id, body.input, run_id=body.run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"planning failed: {exc}") from exc

    payload = result.to_dict()
    if not body.options.return_steps:
        payload["steps"] = []
    return _decorate_and_wrap(
        payload,
        control_loop="plan",
        body_feature_id=body.feature_id,
        body_department_id=body.department_id,
        feature=feature,
        view=view,
        default_layout="generic",
        extra_extensions={
            "api_path": "/v1/planning/runs",
            "agent_type_legacy": "planning",
        },
    )


def _resolve_run_loop(
    *,
    control_loop: str | None,
    agent_type: str | None,
    feature_id: str | None,
    skill_id: str | None,
) -> str:
    """推断规范环 id；失败抛 HTTPException。"""
    raw = control_loop or agent_type
    loop = canonicalize(raw) if raw else None
    if loop in PLATFORM_LOOPS:
        return loop  # type: ignore[return-value]

    if feature_id:
        feature = get_feature(feature_id)
        if not feature:
            raise HTTPException(status_code=404, detail=f"unknown feature: {feature_id}")
        loop = canonicalize(feature.get("agent_type"))
        if loop in PLATFORM_LOOPS:
            return loop  # type: ignore[return-value]

    if skill_id:
        try:
            kind = peek_skill_kind(skill_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        mapped = _KIND_TO_LOOP.get(kind)
        if mapped:
            return mapped

    raise HTTPException(
        status_code=400,
        detail=(
            "无法解析 control_loop：请传 control_loop/agent_type，"
            "或提供可推断环的 feature_id / skill_id"
        ),
    )


@app.post("/v1/runs")
def unified_run(
    body: UnifiedRunRequest,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    """统一运行入口：按 control_loop 分发到各环专用 API（含 plan → planning/runs）。"""
    _check_api_key(x_api_key)
    loop = _resolve_run_loop(
        control_loop=body.control_loop,
        agent_type=body.agent_type,
        feature_id=body.feature_id,
        skill_id=body.skill_id,
    )
    opts = body.options
    common = {
        "feature_id": body.feature_id,
        "department_id": body.department_id,
        "skill_id": body.skill_id,
        "input": body.input,
        "run_id": body.run_id,
    }
    if loop == "plan":
        payload = planning_run(
            body=PlanningRunRequest(
                **common,
                options=PlanningRunOptions(return_steps=opts.return_steps),
            ),
            x_api_key=x_api_key,
        )
    elif loop == "act":
        payload = react_run(
            body=ReactRunRequest(
                **common,
                options=ReactRunOptions(return_steps=opts.return_steps),
            ),
            x_api_key=x_api_key,
        )
    elif loop == "extract":
        payload = extraction_run(
            body=ExtractionRunRequest(
                **common,
                options=ExtractionRunOptions(return_steps=opts.return_steps),
            ),
            x_api_key=x_api_key,
        )
    elif loop == "retrieve":
        payload = rag_run(
            body=RagRunRequest(
                **common,
                options=RagRunOptions(return_steps=opts.return_steps),
            ),
            x_api_key=x_api_key,
        )
    else:
        raise HTTPException(status_code=400, detail=f"unsupported control_loop: {loop}")

    # 子 handler 已是统一 RunResult；补统一入口元数据进 extensions
    ext = dict(payload.get("extensions") or {})
    ext["resolved_via"] = "POST /v1/runs"
    ext["legacy_api_path"] = LOOP_META[loop]["api_path"]
    ext["agent_type_legacy"] = to_legacy(loop)
    payload["extensions"] = ext
    payload["control_loop"] = loop
    return payload


@app.get("/v1/planning/runs/{run_id}")
def planning_run_get(
    run_id: str,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    """按 run_id 回看 Plan 步骤日志与相关 AIOutput（与 react get 同形）。"""
    _check_api_key(x_api_key)
    logs = default_store.list_run_logs(run_id=run_id)
    outputs = default_store.read_ai_outputs(run_id=run_id, limit=50)
    return {
        "run_id": run_id,
        "control_loop": "plan",
        "steps": [x.model_dump(mode="json") if hasattr(x, "model_dump") else x for x in logs],
        "ai_outputs": [
            x.model_dump(mode="json") if hasattr(x, "model_dump") else x for x in outputs
        ],
        "step_count": len(logs),
        "output_count": len(outputs),
    }


@app.get("/v1/react/runs/{run_id}")
def react_run_get(
    run_id: str,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    _check_api_key(x_api_key)
    logs = default_store.list_run_logs(run_id=run_id)
    outputs = default_store.read_ai_outputs(run_id=run_id, limit=50)
    return {
        "run_id": run_id,
        "steps": [x.model_dump(mode="json") if hasattr(x, "model_dump") else x for x in logs],
        "ai_outputs": [
            x.model_dump(mode="json") if hasattr(x, "model_dump") else x for x in outputs
        ],
        "step_count": len(logs),
        "output_count": len(outputs),
    }


@app.get("/v1/capabilities")
def capabilities(
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    _check_api_key(x_api_key)
    rows = default_registry.fetcher.list_capabilities()
    return {
        "capabilities": [
            r.model_dump(mode="json") if hasattr(r, "model_dump") else r for r in rows
        ],
        "count": len(rows),
    }


@app.get("/v1/tools")
def tools(
    tool_class: str | None = Query(
        default=None,
        description="治理三类：read | knowledge | write_govern",
    ),
    category: str | None = Query(
        default=None,
        description="业务域次级标签：master|commerce|service|…",
    ),
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    """平台工具台账：主轴 tool_class，次级 category（业务域）。"""
    _check_api_key(x_api_key)
    if tool_class and tool_class not in TOOL_CLASSES:
        raise HTTPException(
            status_code=400,
            detail=f"unknown tool_class: {tool_class}; expected one of {list(TOOL_CLASSES)}",
        )
    rows = default_registry.list_tools(tool_class=tool_class, category=category)
    summary = default_registry.tool_class_summary()
    return {
        "tools": rows,
        "count": len(rows),
        "tool_classes": list(TOOL_CLASSES),
        "counts": summary["counts"],
        "filter": {"tool_class": tool_class, "category": category},
    }


@app.get("/v1/ops/overview")
def ops_overview(
    control_loop: str | None = Query(
        default=None,
        description="可选：retrieve|act|extract|plan，缺省为平台全局",
    ),
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    """运维看板：健康分 · 四大黄金指标 · 事件关联 · 根因 · 调用链。"""
    _check_api_key(x_api_key)
    from apps.ops_telemetry import build_ops_dashboard

    if control_loop:
        loop = canonicalize(control_loop)
        if loop not in PLATFORM_LOOPS:
            raise HTTPException(
                status_code=400,
                detail=f"unknown control_loop: {control_loop}; expected {list(PLATFORM_LOOPS)}",
            )
        control_loop = loop
    return build_ops_dashboard(loop=control_loop)


@app.get("/v1/ops/loops/{control_loop}")
def ops_loop_dashboard(
    control_loop: str,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    """单控制环运维子页数据（与 overview 同形，scope=该环）。"""
    _check_api_key(x_api_key)
    from apps.ops_telemetry import build_ops_dashboard

    loop = canonicalize(control_loop)
    if loop not in PLATFORM_LOOPS:
        raise HTTPException(
            status_code=404,
            detail=f"unknown control_loop: {control_loop}",
        )
    return build_ops_dashboard(loop=loop)


@app.get("/v1/ops/logs")
def ops_logs(
    limit: int = Query(default=80, ge=1, le=500),
    run_id: str | None = None,
    status: str | None = Query(default=None, description="ok|error|warn|blocked"),
    q: str | None = Query(default=None, description="匹配 step_name / detail 文本"),
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    """运维日志流：来自 SharedStore run_logs。"""
    _check_api_key(x_api_key)
    logs = default_store.list_run_logs(run_id=run_id)
    rows: list[dict[str, Any]] = []
    for x in logs:
        d = x.model_dump(mode="json") if hasattr(x, "model_dump") else dict(x)
        st = str(d.get("step_status") or "").lower()
        detail = d.get("detail") if isinstance(d.get("detail"), dict) else {}
        if status:
            want = status.lower()
            if want == "blocked":
                if not (detail.get("blocked") is True or "block" in st):
                    continue
            elif want not in st:
                continue
        if q:
            blob = f"{d.get('step_name','')} {d.get('run_id','')} {detail}".lower()
            if q.lower() not in blob:
                continue
        rows.append(d)
    rows = rows[-limit:][::-1]  # 最新在前
    return {"logs": rows, "count": len(rows), "filter": {"run_id": run_id, "status": status, "q": q}}


@app.get("/v1/ops/runs")
def ops_runs(
    limit: int = Query(default=30, ge=1, le=200),
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    """近期 run 摘要（链路入口）。"""
    _check_api_key(x_api_key)
    logs = default_store.list_run_logs()
    by_run: dict[str, dict[str, Any]] = {}
    for x in logs:
        rid = x.run_id
        if not rid:
            continue
        row = by_run.setdefault(
            rid,
            {
                "run_id": rid,
                "steps": 0,
                "errors": 0,
                "blocked": False,
                "first_ts": None,
                "last_ts": None,
                "skills": set(),
                "stop_reason": None,
            },
        )
        row["steps"] += 1
        st = str(x.step_status).lower()
        if st in {"error", "fail", "failed"}:
            row["errors"] += 1
        detail = x.detail if isinstance(x.detail, dict) else {}
        if detail.get("blocked") is True:
            row["blocked"] = True
        if detail.get("skill_id"):
            row["skills"].add(str(detail["skill_id"]))
        if detail.get("stop_reason"):
            row["stop_reason"] = detail.get("stop_reason")
        ts = x.step_ts.isoformat() if getattr(x, "step_ts", None) else None
        if ts:
            row["first_ts"] = row["first_ts"] or ts
            row["last_ts"] = ts
    runs = []
    for rid, row in by_run.items():
        runs.append(
            {
                **row,
                "skills": sorted(row["skills"]),
            }
        )
    runs.sort(key=lambda r: r.get("last_ts") or "", reverse=True)
    runs = runs[:limit]
    return {"runs": runs, "count": len(runs)}


@app.get("/v1/ops/runs/{run_id}")
def ops_run_detail(
    run_id: str,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    """单次 run 链路：调用链 + 步骤时间线 + 关联 AIOutput。"""
    _check_api_key(x_api_key)
    from apps.ops_telemetry import build_ops_run_trace

    return build_ops_run_trace(run_id)


@app.get("/v1/ai-outputs")
def ai_outputs_get(
    consumer_skill: str | None = None,
    producer_skill: str | None = None,
    customer_id: str | None = None,
    vin: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    _check_api_key(x_api_key)
    rows = default_store.read_ai_outputs(
        consumer_skill=consumer_skill,
        producer_skill=producer_skill,
        customer_id=customer_id,
        vin=vin,
        limit=limit,
    )
    return {
        "ai_outputs": [
            r.model_dump(mode="json") if hasattr(r, "model_dump") else r for r in rows
        ],
        "count": len(rows),
    }


@app.post("/v1/ai-outputs/read")
def ai_outputs_read(
    body: AiOutputsReadRequest,
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> dict[str, Any]:
    _check_api_key(x_api_key)
    rows = default_store.read_ai_outputs(
        consumer_skill=body.consumer_skill,
        producer_skill=body.producer_skill,
        customer_id=body.customer_id,
        vin=body.vin,
        limit=body.limit,
    )
    return {
        "ai_outputs": [
            r.model_dump(mode="json") if hasattr(r, "model_dump") else r for r in rows
        ],
        "count": len(rows),
    }


# ---- UI routes ----

@app.get("/business", response_class=HTMLResponse)
def business_page() -> FileResponse:
    return FileResponse(_ui("business.html"))


@app.get("/ops", response_class=HTMLResponse)
def ops_page() -> FileResponse:
    return FileResponse(_ui("ops.html"))


@app.get("/ops/embed", response_class=HTMLResponse)
def ops_embed_page() -> FileResponse:
    return FileResponse(_ui("ops.html"))


@app.get("/logic", response_class=HTMLResponse)
def logic_page() -> FileResponse:
    return FileResponse(_ui("logic.html"))


@app.get("/logic/architecture", response_class=HTMLResponse)
def logic_architecture_page() -> FileResponse:
    return FileResponse(_ui("logic-architecture.html"))


@app.get("/logic/solution", response_class=HTMLResponse)
def logic_solution_page() -> FileResponse:
    return FileResponse(_ui("logic-solution.html"))


@app.get("/logic/risk", response_class=HTMLResponse)
def logic_risk_page() -> FileResponse:
    return FileResponse(_ui("logic-risk.html"))


@app.get("/ui", response_class=HTMLResponse)
def ui_page() -> RedirectResponse:
    return RedirectResponse(url="/business?department=service", status_code=307)


@app.get("/embed", response_class=HTMLResponse)
def embed_page() -> RedirectResponse:
    return RedirectResponse(url="/business?department=service", status_code=307)


@app.get("/")
def root() -> RedirectResponse:
    """浏览器打开根路径时直接进入逻辑讲解页（避免看到 JSON / Not Found）。"""
    return RedirectResponse(url="/logic", status_code=307)
