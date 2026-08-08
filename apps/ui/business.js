/* 青枢 AI 工作台 · 业务主管：部门 → 功能列 → 子页 */

const qs = new URLSearchParams(location.search);
const state = {
  departments: [],
  departmentId: qs.get("department") || "service",
  features: [],
  flows: [],
  /** null | feature_id | "__guide__" */
  selectedId: qs.get("feature") || null,
  currentFeature: null,
};

const el = {
  deptNav: document.getElementById("dept-nav"),
  deptIntro: document.getElementById("dept-intro"),
  railList: document.getElementById("feature-rail-list"),
  railSub: document.getElementById("rail-sub"),
  viewEmpty: document.getElementById("view-empty"),
  viewFeature: document.getElementById("view-feature"),
  viewGuide: document.getElementById("view-guide"),
  featureCrumb: document.getElementById("feature-crumb"),
  featureBadges: document.getElementById("feature-badges"),
  featureTitle: document.getElementById("feature-title"),
  featurePurpose: document.getElementById("feature-purpose"),
  featureRunHint: document.getElementById("feature-run-hint"),
  featureActions: document.getElementById("feature-actions"),
  guideCrumb: document.getElementById("guide-crumb"),
  runner: document.getElementById("runner"),
  text: document.getElementById("input-text"),
  customer: document.getElementById("input-customer"),
  vin: document.getElementById("input-vin"),
  dealer: document.getElementById("input-dealer"),
  channel: document.getElementById("input-channel"),
  order: document.getElementById("input-order"),
  payloadBox: document.getElementById("payload-box"),
  payload: document.getElementById("input-payload"),
  status: document.getElementById("status"),
  answer: document.getElementById("answer"),
  kv: document.getElementById("kv"),
  board: document.getElementById("board"),
  steps: document.getElementById("steps"),
  runBtn: document.getElementById("btn-run"),
  sampleBtn: document.getElementById("btn-sample"),
  closeBtn: document.getElementById("btn-close-runner"),
};

const PHASE_ORDER = [
  { id: "demo", title: "可试用", pill: "pill-ok" },
  { id: "phase2", title: "二期", pill: "pill-phase2" },
  { id: "phase3", title: "三期", pill: "pill-phase3" },
];

const EXTRACTION_SKILLS = new Set(["ticket_fields", "voc_entities", "voc_tagging"]);
const RAG_SKILLS = new Set(["repair_kb", "policy_kb", "hr_rules"]);
const PLAN_SKILLS = new Set(["renewal_plan"]);

/** 业务向关系说明（去掉技术词） */
const REL_EXPLAIN = {
  parallel_alt: "与同目标的其它能力可分别试用，互不替代。",
  parallel_producer: "本项会把结果写入共用信息，其它部门可单独读取。",
  parallel_showcase: "规划中能力，与同部门其它项并列展示。",
  parallel_orthogonal: "与本部门主流程并行存在，可独立使用。",
  parallel_optional: "可与相邻能力并存，不替代触达评估。",
  sequence_upstream: "建议先完成本项，再使用依赖共用信息的后续能力。",
  sequence_downstream: "建议先完成前置登记，再使用本项。",
  standalone: "独立能力，一次试用即可完成。",
};

function isExtractionFeature(f) {
  return (
    f?.agent_type === "extract" ||
    f?.agent_type === "extraction" ||
    EXTRACTION_SKILLS.has(f?.skill_id)
  );
}

function isRagFeature(f) {
  return (
    f?.agent_type === "retrieve" ||
    f?.agent_type === "rag" ||
    RAG_SKILLS.has(f?.skill_id)
  );
}

function isPlanFeature(f) {
  return (
    f?.agent_type === "plan" ||
    f?.agent_type === "planning" ||
    PLAN_SKILLS.has(f?.skill_id)
  );
}

function runEndpointFor(f) {
  if (isExtractionFeature(f)) return "/v1/extraction/runs";
  if (isRagFeature(f)) return "/v1/rag/runs";
  if (isPlanFeature(f)) return "/v1/planning/runs";
  return "/v1/react/runs";
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function syncUrl() {
  const u = new URL(location.href);
  u.searchParams.set("department", state.departmentId);
  if (state.selectedId) u.searchParams.set("feature", state.selectedId);
  else u.searchParams.delete("feature");
  history.replaceState(null, "", u);
}

function currentDept() {
  return state.departments.find((d) => d.department_id === state.departmentId);
}

function featurePhase(f) {
  if (f.phase === "demo" || f.phase === "phase2" || f.phase === "phase3") return f.phase;
  if (f.demo_ready || f.status === "demo") return "demo";
  if (f.phase_label === "三期" || f.agent_type === "vision") return "phase3";
  return "phase2";
}

function phaseLabelOf(f) {
  const p = featurePhase(f);
  if (p === "demo") return "可试用";
  if (p === "phase3") return "三期";
  return "二期";
}

/** 业务展示名：去掉技术后缀与黑话 */
function displayName(f) {
  if (!f) return "";
  const map = {
    "F-SVC-001-EXT": "智能填单（结构化）",
    "F-SVC-002": "智能辅助回答",
    "F-SVC-004": "维修知识库问答",
    "F-UO-017": "主动触达评估",
    "F-UO-001": "续费外呼任务",
    "F-UO-009": "App 智能问答",
    "F-POL-RAG": "政策口径问答",
    "F-VOC-002": "客户原声整理",
    "F-X-WRITE": "共用信息写入",
    "F-X-MD": "客户车辆档案查询",
  };
  if (map[f.feature_id]) return map[f.feature_id];
  return String(f.name || "")
    .replace(/\s*[·・]\s*(Extraction|RAG|ReAct|Agent).*$/i, "")
    .replace(/（投诉闸门）/g, "")
    .replace(/Agent\s*/g, "")
    .trim();
}

function softenText(s) {
  return String(s || "")
    .replace(/共享产出写入/g, "共用信息写入")
    .replace(/共享产出/g, "共用信息")
    .replace(/共享层/g, "共用信息")
    .replace(/产出资产化，供他\s*功能\s*订阅/g, "把结果写入共用信息，供其它能力读取")
    .replace(/产出资产化，供他 Skill 订阅/g, "把结果写入共用信息，供其它能力读取")
    .replace(/原声结构化：标签\/情感\/主题\/风险/g, "把客户原声整理成业务标记、情绪与风险提示")
    .replace(/坐席侧维修知识库问答（带引用）/g, "坐席侧维修知识问答，并标注参考资料")
    .replace(/\bRAG\b/g, "知识问答")
    .replace(/\bReAct\b/g, "")
    .replace(/\bExtraction\b/g, "")
    .replace(/\bAgent\b/g, "")
    .replace(/\bSkill\b/g, "功能")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function softenSkillName(id) {
  const map = {
    renewal_plan: "续费触达评估",
    fill_ticket: "智能填单",
    ticket_fields: "智能填单（结构化）",
    voc_entities: "客户原声整理",
    repair_kb: "维修知识问答",
    policy_kb: "政策口径问答",
    hr_rules: "人资制度问答",
    shared_write: "共用信息写入",
    master_data: "客户车辆档案查询",
  };
  return map[String(id || "").trim()] || String(id || "");
}

/** 把技术说明转成业务可读指引（去掉缩写与接口） */
function toBusinessGuide(f) {
  const parts = [];
  if (f.purpose) parts.push(softenText(f.purpose));
  const rel = REL_EXPLAIN[f.orchestration];
  if (rel) parts.push(rel);
  if (f.demo_ready) {
    parts.push("点击下方「开始试用」即可体验；仅运行当前这一项。");
  } else {
    parts.push("当前为路线图能力，可先了解用途，后续版本开放试用。");
  }
  return parts.join(" ");
}

function softDeptIntro(flows) {
  const dept = currentDept();
  const name = dept?.name || "本部门";
  if (!flows?.length) {
    return `${name}的能力列在左侧。点进一项可看说明；可试用项可直接体验。各项独立使用，不会自动连着跑。`;
  }
  return `${name}的能力列在左侧。各部门结果写入共用信息，其它能力另开一次读取，而不是自动连跑——这是跨部门协同的关键。点进左侧任一项可查看说明并试用。`;
}

function showGuideInDept() {
  // 指南挂在服务 / 用户运营两个相关部门
  return state.departmentId === "service" || state.departmentId === "user_ops";
}

function renderDeptNav() {
  el.deptNav.innerHTML = state.departments
    .map((d, i) => {
      const active = d.department_id === state.departmentId ? "active" : "";
      const sep = i > 0 ? '<span class="dept-sep" aria-hidden="true"></span>' : "";
      return `${sep}<button type="button" class="dept-nav-btn ${active}" data-dept="${d.department_id}">
        ${escapeHtml(d.name)}
      </button>`;
    })
    .join("");
  el.deptNav.querySelectorAll("[data-dept]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.departmentId = btn.dataset.dept;
      state.selectedId = null;
      state.currentFeature = null;
      el.runner.hidden = true;
      loadFeatures();
    });
  });
}

function renderDeptIntro() {
  if (!el.deptIntro) return;
  el.deptIntro.hidden = false;
  el.deptIntro.innerHTML = `<p>${escapeHtml(softDeptIntro(state.flows))}</p>`;
}

function railItems() {
  const items = [];
  if (showGuideInDept()) {
    items.push({
      id: "__guide__",
      name: "跨部门协同：投诉未结则暂停触达",
      phase: "demo",
      kind: "guide",
    });
  }
  const groups = { demo: [], phase2: [], phase3: [] };
  for (const f of state.features) {
    groups[featurePhase(f)].push(f);
  }
  for (const p of PHASE_ORDER) {
    for (const f of groups[p.id]) {
      items.push({
        id: f.feature_id,
        name: displayName(f),
        phase: p.id,
        kind: "feature",
        demo_ready: !!f.demo_ready,
      });
    }
  }
  return items;
}

function renderFeatureRail() {
  const dept = currentDept();
  el.railSub.textContent = dept ? dept.name : "请选择部门";
  const items = railItems();
  if (!items.length) {
    el.railList.innerHTML = `<div class="empty-card">暂无功能</div>`;
    return;
  }

  const byPhase = { demo: [], phase2: [], phase3: [] };
  for (const item of items) {
    const ph = item.kind === "guide" ? "demo" : item.phase;
    byPhase[ph].push(item);
  }

  let html = "";
  for (const p of PHASE_ORDER) {
    const rows = byPhase[p.id];
    if (!rows.length) continue;
    html += `<div class="rail-phase" data-phase-label="${p.id}">${escapeHtml(p.title)}</div>`;
    for (const item of rows) {
      const active = state.selectedId === item.id ? "active" : "";
      const readyCls = p.id === "demo" ? "rail-item-demo" : "rail-item-planned";
      html += `<button type="button" class="rail-item ${readyCls} ${active}" data-id="${escapeHtml(item.id)}">
        <span class="rail-item-name">${escapeHtml(item.name)}</span>
      </button>`;
    }
  }

  el.railList.innerHTML = html;
  el.railList.querySelectorAll("[data-id]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.selectedId = btn.dataset.id;
      el.runner.hidden = true;
      if (el.closeBtn) el.closeBtn.hidden = true;
      syncUrl();
      renderFeatureRail();
      renderMainView();
    });
  });
}

function renderMainView() {
  const isGuide = state.selectedId === "__guide__";
  const f = state.features.find((x) => x.feature_id === state.selectedId) || null;

  el.viewEmpty.hidden = !!(isGuide || f);
  el.viewGuide.hidden = !isGuide;
  el.viewFeature.hidden = !f;

  if (isGuide) {
    const dept = currentDept();
    el.guideCrumb.textContent = `业务主管 · ${dept?.name || ""} · 业务操作指南`;
    return;
  }

  if (!f) return;

  const dept = currentDept();
  const phase = phaseLabelOf(f);
  const nice = displayName(f);
  el.featureCrumb.textContent = `业务主管 · ${dept?.name || ""} · ${nice}`;
  el.featureBadges.innerHTML = `<span class="pill ${
    featurePhase(f) === "demo" ? "pill-ok" : featurePhase(f) === "phase3" ? "pill-phase3" : "pill-phase2"
  }">${escapeHtml(phase)}</span>`;
  el.featureTitle.textContent = nice;
  el.featurePurpose.textContent = softenText(f.purpose || "");
  el.featureRunHint.textContent = f.demo_ready
    ? "填写示例或自定义内容后，点击「开始试用」。仅运行当前这一项。"
    : "";

  // 上方说明栏仅作介绍；试用入口在下方试用区
  el.featureActions.innerHTML = "";
  if (f.demo_ready) {
    openRunner(f);
  } else {
    el.runner.hidden = true;
    el.closeBtn.hidden = true;
    el.featureActions.innerHTML = `<span class="pill pill-muted">路线图 · 暂不可试用</span>`;
  }
}

function fieldVisible(name, fields) {
  return (fields || []).includes(name);
}

function openRunner(f) {
  state.currentFeature = f;
  el.runBtn.disabled = !f.demo_ready;
  el.runner.hidden = false;
  el.closeBtn.hidden = false;
  el.runner.className = `runner card layout-${f.layout || "generic"}`;
  el.runBtn.textContent = "开始试用";

  const label = document.getElementById("label-input-text");
  if (label) label.textContent = isRagFeature(f) ? "问题" : "内容";

  const fields = f.input_fields || ["text"];
  document.getElementById("wrap-customer").hidden = !fieldVisible("customer_id", fields);
  document.getElementById("wrap-vin").hidden = !fieldVisible("vin", fields);
  document.getElementById("wrap-dealer").hidden = !fieldVisible("dealer_id", fields);
  document.getElementById("wrap-channel").hidden = !fieldVisible("channel", fields);
  document.getElementById("wrap-order").hidden = !fieldVisible("order_id", fields);
  el.payloadBox.hidden = f.skill_id !== "shared_write";
  el.text.placeholder = softenText(f.placeholder_text || "");
  fillSample();
  el.answer.classList.remove("answer-rich");
  el.answer.textContent = "尚未试用。";
  el.kv.innerHTML = "";
  el.board.innerHTML = "";
  el.steps.innerHTML = "";
  el.status.textContent = "就绪";
  el.status.className = "status-line";
}

/** 补充信息：业务可读行 → 内部 payload */
function formatSoftPayload(payload) {
  if (!payload || typeof payload !== "object") return "";
  const note = payload.note === "platform-demo" ? "平台演示" : payload.note || "";
  const tag = String(payload.tag_id || "").replace(/^TAG[-_]?/, "");
  const lines = [];
  if (note) lines.push(`备注：${note}`);
  if (payload.customer_id) lines.push(`客户编号：${payload.customer_id}`);
  if (tag) lines.push(`业务标记：${tag}`);
  return lines.join("\n");
}

function parseSoftPayload(raw) {
  const text = String(raw || "").trim();
  if (!text) return undefined;
  if (text.startsWith("{")) return JSON.parse(text);
  const out = {};
  for (const line of text.split(/\n+/)) {
    const m = line.match(/^([^：:]+)[:：]\s*(.+)$/);
    if (!m) continue;
    const k = m[1].trim();
    const v = m[2].trim();
    if (k === "备注") out.note = v === "平台演示" ? "platform-demo" : v;
    else if (k === "客户编号") out.customer_id = v;
    else if (k === "业务标记") out.tag_id = v.startsWith("TAG-") ? v : `TAG-${v}`;
  }
  return Object.keys(out).length ? out : undefined;
}

function fillSample() {
  const f = state.currentFeature;
  if (!f) return;
  const s = f.sample || {};
  let text = s.query || s.text || "";
  text = text
    .replace(/renewal_plan/g, "续费触达评估")
    .replace(/只读消费/g, "读取使用")
    .replace(/共享产出/g, "共用信息");
  el.text.value = text;
  el.customer.value = s.customer_id || "";
  el.vin.value = s.vin || "";
  el.dealer.value = s.dealer_id || "";
  el.channel.value = s.channel || "";
  el.order.value = s.order_id || "";
  el.payload.value = s.payload ? formatSoftPayload(s.payload) : "";
}

function collectInput() {
  const f = state.currentFeature;
  const text = el.text.value.trim();
  const input = isRagFeature(f) ? { query: text, text } : { text };
  if (!document.getElementById("wrap-customer").hidden && el.customer.value.trim()) {
    input.customer_id = el.customer.value.trim();
  }
  if (!document.getElementById("wrap-vin").hidden && el.vin.value.trim()) {
    input.vin = el.vin.value.trim();
  }
  if (!document.getElementById("wrap-dealer").hidden && el.dealer.value.trim()) {
    input.dealer_id = el.dealer.value.trim();
  }
  if (!document.getElementById("wrap-channel").hidden && el.channel.value.trim()) {
    input.channel = el.channel.value.trim();
  }
  if (!document.getElementById("wrap-order").hidden && el.order.value.trim()) {
    input.order_id = el.order.value.trim();
  }
  if (f?.skill_id === "shared_write") {
    const parsed = parseSoftPayload(el.payload.value);
    if (parsed) input.payload = parsed;
  }
  return input;
}

function kvItem(k, v) {
  if (v === undefined || v === null || v === "") return "";
  return `<div class="item"><div class="k">${escapeHtml(k)}</div><div class="v">${escapeHtml(String(v))}</div></div>`;
}

function escapeRegExp(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** 业务侧标签/字段映射（展示层；底层知识与评测 ID 不改） */
const BIZ_TERM_MAP = [
  [/is_smart_vehicle\s*=\s*true/gi, "智能车"],
  [/is_smart_vehicle\s*=\s*false/gi, "非智能车"],
  [/`?is_smart_vehicle`?/gi, "是否为智能车"],
  [/intent_level\s*=\s*high/gi, "高意向"],
  [/intent_level\s*=\s*medium/gi, "中意向"],
  [/intent_level\s*=\s*low/gi, "低意向"],
  [/\bnon_smart\b/gi, "非智能车"],
  [/read_ai_outputs/gi, "读取共用信息"],
  [/\bAIOutput\b/g, "共用信息记录"],
  [/ai_output_ids?/gi, "共用信息编号"],
  [/consumer_allow/gi, "可读能力"],
  [/\bpayload\b/gi, "内容详情"],
  [/customer_id/gi, "客户编号"],
  [/tag_id/gi, "业务标记"],
  [/\bsentiment\b/gi, "情绪"],
  [/\bplatform-demo\b/gi, "平台演示"],
  [/\brenewal_plan\b/g, "续费触达评估"],
  [/\bfill_ticket\b/g, "智能填单"],
  [/\bticket_fields\b/g, "智能填单（结构化）"],
  [/\bvoc_entities\b/g, "客户原声整理"],
  [/\bshared_write\b/g, "共用信息写入"],
  [/只读消费/g, "读取使用"],
  [/TAG[-_]?投诉未结/g, "「投诉未结」标记"],
  [/TAG[-_]?绑车失败/g, "「绑车失败」标记"],
  [/TAG[-_]?续航短/g, "「续航偏短」标记"],
  [/TAG[-_]?舆情风险/g, "「舆情风险」标记"],
  [/TAG[-_]?安全隐患/g, "「安全隐患」标记"],
  [/TAG[-_]?三包争议/g, "「三包争议」标记"],
  [/TAG[-_]?非专卖/g, "「非专卖」标记"],
  [/TAG[-_]?VI违规/g, "「门店形象违规」标记"],
  [/TAG[-_]?演示/g, "「演示」标记"],
  [/TAG[-_]?([^\s`，,。；;）)\]]+)/g, "「$1」标记"],
  [/BMS_OT_01/g, "电池高温告警"],
  [/\bSOH\b/g, "电池健康度"],
  [/\bOTA\b/g, "系统版本"],
  [/\bBMS\b/g, "电池系统"],
  [/\bMCU\b/g, "电机控制器"],
  [/\bVIN\b/g, "车辆识别码"],
  [/\bIoT\b/g, "车联网"],
  [/(^|[^\w])neg([^\w]|$)/g, "$1负面$2"],
  [/(^|[^\w])pos([^\w]|$)/g, "$1正面$2"],
  [/(^|[^\w])neu([^\w]|$)/g, "$1中性$2"],
];

/** 把知识片段 ID 转成可读资料名（展示层映射，不改底层数据） */
function humanizeChunkId(id) {
  const raw = String(id || "").replace(/^kb_chunk_id\s*=\s*/i, "").trim();
  const m = raw.match(/^(?:[a-z]+__)?([^#]+?)(?:#c(\d+))?$/i);
  if (m) {
    const name = m[1].replace(/[-_]/g, " ").replace(/\s+/g, "").trim() || "内部知识";
    const n = m[2] ? Number(m[2]) : 0;
    return n ? `${name}（资料 ${n}）` : name;
  }
  return "内部知识资料";
}

function citeTitle(c) {
  return softenText(c?.title || c?.doc_title || humanizeChunkId(c?.kb_chunk_id || c?.doc_id || ""));
}

function uniqueCiteTitles(citations) {
  const titles = [];
  const seen = new Set();
  for (const c of citations || []) {
    const t = citeTitle(c);
    if (!t || seen.has(t)) continue;
    seen.add(t);
    titles.push(t);
  }
  return titles;
}

/** 只展示正文实际用到的资料名；避免检索噪声混入上方参考条 */
function relevantCiteTitles(text, citations) {
  const titles = uniqueCiteTitles(citations);
  if (!titles.length) return titles;
  const body = String(text || "");
  const hit = titles.filter(
    (t) => body.includes(t) || body.includes(`《${t}》`) || body.includes(t.replace(/\s+/g, ""))
  );
  return hit.length ? hit : titles.slice(0, 1);
}

function buildCiteMap(citations) {
  const map = new Map();
  for (const c of citations || []) {
    const id = String(c.kb_chunk_id || c.doc_id || "").trim();
    if (!id) continue;
    const title = citeTitle(c);
    map.set(id, title);
    map.set(`kb_chunk_id=${id}`, title);
  }
  return map;
}

/** 上方已有参考资料时，去掉正文里的重复书名/引用段 */
function stripRedundantCitations(text, citeTitles) {
  let s = String(text || "");
  if (!citeTitles?.length) return s;

  // 去掉「引用/参考资料」块（仅书名/技术引用行），保留其后的「建议下一步」等
  s = s.replace(
    /(?:^|\n)[ \t]*(?:#{1,3}[ \t]*)?(?:\*\*)?(?:\d+[\.、][ \t]*)?(?:参考资料|引用)(?:\*\*)?[ \t]*(?:\n[ \t]*(?:[-*•][ \t]*)?(?:《[^》]+》|kb_chunk_id\b[^\n]*|参考[:：][^\n]*))*/gi,
    "\n"
  );

  for (const t of citeTitles) {
    const esc = escapeRegExp(t);
    s = s.replace(new RegExp(`[（(]\\s*《${esc}》\\s*[）)]`, "g"), "");
    s = s.replace(new RegExp(`（参考[:：]\\s*《?${esc}》?）`, "g"), "");
    s = s.replace(new RegExp(`参考[:：]\\s*《${esc}》`, "g"), "");
    s = s.replace(new RegExp(`^[ \\t]*[-*•]?\\s*《${esc}》\\s*$`, "gm"), "");
  }

  // 其它重复书名括号与「根据…《…》」开场
  s = s.replace(/[（(]\s*《[^》]+》\s*[）)]/g, "");
  s = s.replace(/根据[^《\n]{0,16}《[^》]+》(?:文档|排障文档)?/g, "根据相关资料");
  s = s.replace(/依据[^《\n]{0,16}《[^》]+》(?:文档|排障文档)?/g, "依据相关资料");
  s = s.replace(/根据相关资料(?:排障)?文档/g, "根据相关资料");
  s = s.replace(/依据相关资料(?:排障)?文档/g, "依据相关资料");
  s = s.replace(/^[ \t]*[-*•]?\s*《[^》]+》\s*$/gm, "");
  s = s.replace(/该\s*车辆识别码/g, "该车");
  s = s.replace(/\n{3,}/g, "\n\n");
  return s.trim();
}

/** 去掉技术编号与术语，保留业务可读表达 */
function softenAnswerText(text, citations) {
  let s = String(text || "");
  const map = buildCiteMap(citations);
  const titles = relevantCiteTitles(text, citations);

  // 整行技术引用先转成书名行（随后若上方已有参考资料会被去掉）
  s = s.replace(
    /^[ \t]*kb_chunk_id\s*[=:：]\s*(.+?)\s*$/gim,
    (_, rest) => {
      const raw = String(rest).trim();
      const idMatch = raw.match(/([\w\u4e00-\u9fff\-]+__[\w\u4e00-\u9fff\-]+#c\d{4})/);
      if (idMatch) {
        const title = map.get(idMatch[1]) || humanizeChunkId(idMatch[1]);
        return `- 《${title}》`;
      }
      const book = raw.match(/《([^》]+)》/);
      if (book) return `- 《${book[1]}》`;
      const titled = raw.match(/标题[:：]\s*([^）)]+)/);
      if (titled) return `- 《${titled[1].replace(/\s*[›>].*$/, "").trim()}》`;
      return `- 《${humanizeChunkId(raw)}》`;
    }
  );

  s = s.replace(/[（(]\s*依据[:：]\s*kb_chunk_id\s*[=:：]\s*([^）)]+?)\s*[）)]/g, (_, id) => {
    const key = String(id).trim();
    const title = map.get(key) || humanizeChunkId(key);
    return `（参考：${title}）`;
  });
  s = s.replace(/依据[:：]\s*kb_chunk_id\s*[=:：]\s*([^\s，,。；;）)\]]+)/g, (_, id) => {
    const title = map.get(String(id).trim()) || humanizeChunkId(id);
    return `参考：${title}`;
  });
  s = s.replace(/kb_chunk_id\s*[=:：]\s*/g, "");
  s = s.replace(/([\w\u4e00-\u9fff\-]+__[\w\u4e00-\u9fff\-]+#c\d{4})/g, (m) => {
    const title = map.get(m) || humanizeChunkId(m);
    return `《${title}》`;
  });
  s = s.replace(/（标题[:：][^）]*）/g, "");

  s = s.replace(/依据检索片段\s*#?c?(\d{3,4})/gi, (_, n) => {
    const needle = `#c${String(n).padStart(4, "0")}`;
    for (const [id, title] of map.entries()) {
      if (String(id).includes(needle)) return `参考：${title}`;
    }
    return "参考：相关知识资料";
  });
  s = s.replace(/检索片段\s*#?c?(\d{3,4})/gi, (_, n) => {
    const needle = `#c${String(n).padStart(4, "0")}`;
    for (const [id, title] of map.entries()) {
      if (String(id).includes(needle)) return `《${title}》`;
    }
    return "相关知识资料";
  });

  for (const [re, to] of BIZ_TERM_MAP) s = s.replace(re, to);
  // 先去掉代码反引号，再做中文润色（否则 `TAG-xxx` 映射后仍被反引号挡住）
  s = s.replace(/`([^`]+)`/g, "$1");

  s = s
    .replace(/【系统补全引用】/g, "【参考资料】")
    .replace(/【引用】/g, "【参考资料】")
    .replace(
      /(^|\n)\s*(?:#{1,3}\s*)?(?:\*\*)?(?:\d+[\.、]\s*)?引用(?:\*\*)?\s*(?=\n|$)/g,
      "$1参考资料"
    )
    .replace(/\*\*依据知识库的排查\/处理建议\*\*/g, "**排查与处理建议**")
    .replace(/依据知识库的排查\/处理建议/g, "排查与处理建议")
    .replace(/\*\*问题复述\*\*/g, "**问题理解**")
    .replace(/问题复述/g, "问题理解")
    .replace(/电池健康度（SOH）/g, "电池健康度")
    .replace(/OTA\s*版本/g, "系统版本")
    .replace(/（SOH）/g, "")
    .replace(/是否满足\s*智能车/g, "是否为智能车")
    .replace(/查\s*车辆识别码\s*是否\s*(?:为)?智能车（是否为智能车）/g, "确认该车是否为智能车")
    .replace(/车辆识别码\s*是否\s*(?:为)?智能车（是否为智能车）/g, "车辆是否为智能车")
    .replace(/是否为智能车（智能车）/g, "是否为智能车")
    .replace(/是否\s*智能车（是否为智能车）/g, "是否为智能车")
    .replace(/是否\s*(?:为)?智能车（智能车）/g, "是否为智能车")
    .replace(/智能车（智能车）/g, "智能车")
    .replace(/确认\s*车辆识别码\s*是否为智能车/g, "确认该车是否为智能车")
    .replace(/是否为\s+智能车/g, "是否为智能车")
    .replace(/查\s*车辆识别码\s*是否\s*(?:为)?智能车/g, "确认该车是否为智能车")
    .replace(/是否\s*智能车\s*[；;]/g, "是否为智能车；")
    .replace(/打标签\s*「([^」]+)」\s*标记(?:\s*标签)?/g, "标记「$1」")
    .replace(/打\s*「([^」]+)」\s*标记(?:\s*标签)?/g, "标记「$1」")
    .replace(/是否打\s*「([^」]+)」\s*标记(?:\s*标签)?/g, "是否标记「$1」")
    .replace(/可评估(?:是否)?打\s*「/g, "可评估是否标记「")
    .replace(/评估是否打\s*「/g, "评估是否标记「")
    .replace(/评估打\s*「/g, "评估标记「")
    .replace(/可打\s*「/g, "可标记「")
    .replace(/标记\s*「([^」]+)」\s*标记(?:\s*标签)?/g, "标记「$1」")
    .replace(/是否标记\s*「([^」]+)」\s*标记(?:\s*标签)?/g, "是否标记「$1」")
    .replace(/共享产出/g, "共用信息")
    .replace(/共享层/g, "共用信息")
    .replace(/一线动作/g, "建议动作")
    .replace(/一线可/g, "门店可")
    .replace(/建议一线/g, "建议门店")
    .replace(/转一线专席/g, "转门店专席")
    .replace(/本 Skill/g, "本功能")
    .replace(/\bSkill\b/g, "功能")
    .replace(/一期不强制查主数据/g, "当前不强制查询客户车辆档案")
    .replace(/主数据/g, "客户车辆档案")
    .replace(/电池健康度（电池健康度）/g, "电池健康度")
    .replace(/系统版本\s*版本/g, "系统版本")
    .replace(/电池高温告警\s*温升告警/g, "电池高温告警")
    .replace(/（引用[:：]/g, "（参考：")
    .replace(/引用[:：]\s*《/g, "参考：《");

  s = stripRedundantCitations(s, titles);
  return s;
}

function isMdTableSep(line) {
  return /^\s*\|?\s*:?-{3,}.*?\|/.test(line);
}

function splitMdRow(line) {
  let s = String(line).trim();
  if (s.startsWith("|")) s = s.slice(1);
  if (s.endsWith("|")) s = s.slice(0, -1);
  return s.split("|").map((c) => c.trim());
}

function inlineMd(escaped) {
  return escaped
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

/** 轻量 Markdown → HTML（业务展示用：标题/列表/表格/加粗；序号连续重排） */
function renderBusinessMarkdown(src) {
  const lines = String(src || "").replace(/\r\n/g, "\n").split("\n");
  const out = [];
  let i = 0;
  let listType = null;
  let stepN = 0;

  const closeList = () => {
    if (listType) {
      out.push(listType === "ol" ? "</ol>" : "</ul>");
      listType = null;
    }
  };

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      closeList();
      i += 1;
      continue;
    }

    // 跳过已抽到上方的「参考资料」残留标题
    if (/^(?:#{1,3}\s+)?(?:\*\*)?(?:\d+[\.、]\s*)?(?:参考资料|引用)(?:\*\*)?\s*$/.test(trimmed)) {
      closeList();
      i += 1;
      while (i < lines.length) {
        const t = lines[i].trim();
        if (!t || /^《[^》]+》$/.test(t) || /^[-*•]\s*《[^》]+》$/.test(t) || /^kb_chunk/i.test(t)) {
          i += 1;
          continue;
        }
        break;
      }
      continue;
    }

    // 伪表格：连续「现象：原因 → 动作」行
    if (/^.+[:：].+→.+/.test(trimmed)) {
      const rows = [];
      while (i < lines.length && /^.+[:：].+→.+/.test(lines[i].trim())) {
        const row = lines[i].trim();
        const m = row.match(/^(.+?)[:：]\s*(.+?)\s*→\s*(.+)$/);
        if (m) rows.push([m[1], m[2], m[3]]);
        i += 1;
      }
      if (rows.length) {
        closeList();
        out.push('<div class="biz-table-wrap"><table class="biz-table"><thead><tr>');
        ["现象", "可能原因", "建议动作"].forEach((h) => {
          out.push(`<th>${escapeHtml(h)}</th>`);
        });
        out.push("</tr></thead><tbody>");
        rows.forEach((r) => {
          out.push("<tr>");
          r.forEach((c) => out.push(`<td>${inlineMd(escapeHtml(c))}</td>`));
          out.push("</tr>");
        });
        out.push("</tbody></table></div>");
        continue;
      }
    }

    // 表格：表头 + 分隔行 + 数据行
    if (
      trimmed.includes("|") &&
      i + 1 < lines.length &&
      isMdTableSep(lines[i + 1])
    ) {
      closeList();
      const header = splitMdRow(trimmed);
      i += 2;
      const rows = [];
      while (i < lines.length && lines[i].trim().includes("|") && !isMdTableSep(lines[i])) {
        rows.push(splitMdRow(lines[i].trim()));
        i += 1;
      }
      out.push('<div class="biz-table-wrap"><table class="biz-table"><thead><tr>');
      header.forEach((h) => {
        out.push(`<th>${inlineMd(escapeHtml(h))}</th>`);
      });
      out.push("</tr></thead><tbody>");
      rows.forEach((row) => {
        out.push("<tr>");
        header.forEach((_, idx) => {
          out.push(`<td>${inlineMd(escapeHtml(row[idx] || ""))}</td>`);
        });
        out.push("</tr>");
      });
      out.push("</tbody></table></div>");
      continue;
    }

    const h = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (h) {
      closeList();
      const level = h[1].length;
      const title = h[2].replace(/^\d+[\.、]\s*/, "");
      stepN += 1;
      out.push(
        `<h${level + 2} class="biz-h"><span class="biz-n">${stepN}.</span> ${inlineMd(escapeHtml(title))}</h${level + 2}>`
      );
      i += 1;
      continue;
    }

    const sec = trimmed.match(/^[【\[](.+?)[】\]]\s*$/);
    if (sec) {
      closeList();
      stepN += 1;
      out.push(
        `<h4 class="biz-h"><span class="biz-n">${stepN}.</span> ${inlineMd(escapeHtml(sec[1]))}</h4>`
      );
      i += 1;
      continue;
    }

    // 顶级序号：不依赖 <ol>（中间插入列表会导致反复从 1 开始），自行连续编号
    const ol = trimmed.match(/^(\d+)[\.、]\s+(.+)$/);
    if (ol) {
      closeList();
      stepN += 1;
      const rawBody = ol[2];
      const isSection = /[：:]\s*$/.test(rawBody) || rawBody.length <= 40;
      const body = rawBody.replace(/[：:]\s*$/, "").trim();
      if (isSection) {
        out.push(
          `<h4 class="biz-h"><span class="biz-n">${stepN}.</span> ${inlineMd(escapeHtml(body))}</h4>`
        );
      } else {
        out.push(
          `<p class="biz-step"><span class="biz-n">${stepN}.</span> ${inlineMd(escapeHtml(rawBody))}</p>`
        );
      }
      i += 1;
      continue;
    }

    const ul = trimmed.match(/^[-*•]\s+(.+)$/);
    if (ul) {
      if (listType !== "ul") {
        closeList();
        out.push("<ul class='biz-list'>");
        listType = "ul";
      }
      out.push(`<li>${inlineMd(escapeHtml(ul[1]))}</li>`);
      i += 1;
      continue;
    }

    closeList();
    out.push(`<p class="biz-p">${inlineMd(escapeHtml(trimmed))}</p>`);
    i += 1;
  }
  closeList();
  return out.join("") || "<p class='biz-p'>（暂无结果说明）</p>";
}

function formatBusinessAnswer(text, citations) {
  return renderBusinessMarkdown(softenAnswerText(text, citations));
}

function sentimentLabel(v) {
  const s = String(v || "").toLowerCase();
  if (s === "neg" || s === "negative" || s === "负面") return "负面";
  if (s === "pos" || s === "positive" || s === "正面") return "正面";
  if (s === "neu" || s === "neutral" || s === "中性") return "中性";
  return softenAnswerText(String(v || "—"), []);
}

function tryParseJsonObject(text) {
  const t = String(text || "").trim();
  if (!t.startsWith("{") && !t.startsWith("[")) return null;
  try {
    return JSON.parse(t);
  } catch {
    return null;
  }
}

function bizResultRowsFromObject(obj) {
  if (!obj || typeof obj !== "object" || Array.isArray(obj)) return [];
  const rows = [];
  const push = (k, v) => {
    if (v === undefined || v === null || v === "") return;
    rows.push([k, v]);
  };
  const rawTag = obj.tag_name || obj.tag_id;
  if (rawTag != null) {
    const tag = softenAnswerText(String(rawTag), [])
      .replace(/^「/, "")
      .replace(/」标记$/, "")
      .replace(/^TAG[-_]?/, "");
    push("业务标记", tag);
  }
  if (obj.sentiment != null) push("情绪", sentimentLabel(obj.sentiment));
  if (obj.problem_theme != null) push("问题主题", String(obj.problem_theme));
  else if (obj.topic != null) push("主题", softenAnswerText(String(obj.topic), []));
  if (obj.reputation_risk_level != null) {
    push("舆情风险", String(obj.reputation_risk_level));
  } else if (obj.risk != null) {
    push("风险提示", softenAnswerText(String(obj.risk), []));
  }
  if (Array.isArray(obj.secondary_tag_ids) && obj.secondary_tag_ids.length) {
    push(
      "附加标记",
      obj.secondary_tag_ids
        .map((t) =>
          softenAnswerText(String(t), [])
            .replace(/^「/, "")
            .replace(/」标记$/, "")
        )
        .join("、")
    );
  }
  if (obj.needs_human_review === true) push("是否需人工复核", "是");
  if (obj.customer_id != null) push("客户编号", String(obj.customer_id));
  if (obj.note != null) {
    push("备注", obj.note === "platform-demo" ? "平台演示" : String(obj.note));
  }
  if (obj.consumer_allow != null) {
    const list = Array.isArray(obj.consumer_allow)
      ? obj.consumer_allow.map(softenSkillName).join("、")
      : softenSkillName(obj.consumer_allow);
    push("可供读取的能力", list);
  }
  return rows;
}

function renderBizResultTable(rows, summary) {
  if (!rows.length && !summary) return "";
  let html = '<div class="biz-result-card">';
  if (summary) html += `<p class="biz-result-summary">${escapeHtml(summary)}</p>`;
  if (rows.length) {
    html += '<div class="biz-result-grid">';
    for (const [k, v] of rows) {
      html += `<div class="biz-result-item"><div class="k">${escapeHtml(k)}</div><div class="v">${escapeHtml(String(v))}</div></div>`;
    }
    html += "</div>";
  }
  html += "</div>";
  return html;
}

function buildStructuredBusinessView(res) {
  const f = state.currentFeature;
  const ext = res.extensions || {};
  const text = res.final_text || res.final_answer || "";
  const payload = res.payload != null ? res.payload : ext.payload;
  const parsed = tryParseJsonObject(text);
  const rows = [];
  let summary = "";

  if (isExtractionFeature(f)) {
    summary = "已从客户原声中整理出以下业务信息：";
    const rich =
      payload && typeof payload === "object" && !Array.isArray(payload)
        ? payload
        : parsed;
    if (rich) rows.push(...bizResultRowsFromObject(rich));
  } else if (f?.skill_id === "shared_write" || /ai_output_id|consumer_allow|payload|共享\s*AI\s*产出|shared_write/i.test(text)) {
    summary = "共用信息已写入，其它能力可按需读取。";
    let consumers = ext.consumer_allow || payload?.consumer_allow;
    if (!consumers) {
      const m = text.match(/(?:consumer_allow|可读能力)\s*[:=：]\s*\[([^\]]+)\]/i);
      if (m) consumers = m[1];
    }
    if (consumers) {
      const list = Array.isArray(consumers)
        ? consumers
        : String(consumers)
            .replace(/["']/g, "")
            .split(/[,、\s]+/)
            .filter(Boolean);
      rows.push(["可供读取的能力", list.map(softenSkillName).join("、")]);
    }
    if (payload && typeof payload === "object") {
      rows.push(...bizResultRowsFromObject(payload));
    } else {
      const note = text.match(/note\s*=\s*([^\s，,)）]+)/i);
      const cus = text.match(/customer_id\s*=\s*([^\s，,)）]+)/i);
      const tag = text.match(/tag_id\s*=\s*([^\s，,)）]+)/i);
      if (note) rows.push(["备注", note[1] === "platform-demo" ? "平台演示" : note[1]]);
      if (cus) rows.push(["客户编号", cus[1]]);
      if (tag) rows.push(["业务标记", softenAnswerText(tag[1], [])]);
    }
  } else if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
    rows.push(...bizResultRowsFromObject(parsed));
  }

  if (!rows.length) return null;
  return renderBizResultTable(rows, summary);
}

function renderResult(res) {
  const ext = res.extensions || {};
  const text = res.final_text || res.final_answer || "（暂无结果说明）";
  const cites = res.citations || ext.citations || [];
  const gate = res.gate || ext.gate || null;
  const payload = res.payload != null ? res.payload : ext.payload;
  const titles = relevantCiteTitles(text, cites);

  const structured = buildStructuredBusinessView(res);
  el.answer.classList.add("answer-rich");
  if (structured) {
    el.answer.innerHTML = structured;
  } else {
    el.answer.innerHTML = formatBusinessAnswer(text, cites);
  }
  el.status.textContent = res.ok ? "试用完成" : `未完成${res.error ? "：" + res.error : ""}`;
  el.status.className = `status-line ${res.ok ? "ok" : "err"}`;

  let kv = "";
  if (gate) {
    const blocked = gate.blocked === true || gate.allow_outreach === false;
    kv +=
      kvItem("触达结论", blocked ? "已暂停触达" : "允许触达") +
      kvItem("原因", softenAnswerText(gate.reason || "", []));
  }
  // 结构化结果已展示业务标记时，不再重复底部 kv
  if (!structured && payload && typeof payload === "object" && payload.tag_id) {
    kv += kvItem("关联标记", softenAnswerText(String(payload.tag_id), []));
  }
  el.kv.innerHTML = kv;
  // kv 不用等宽字体（避免技术感）
  el.kv.querySelectorAll(".v").forEach((n) => {
    n.style.fontFamily = "var(--font)";
  });

  el.board.innerHTML = "";
  if (gate) {
    const blocked = gate.blocked === true || gate.allow_outreach === false;
    el.board.innerHTML = `
      <div class="metric"><div class="label">触达</div><div class="value" style="font-size:14px">${blocked ? "暂停" : "放行"}</div></div>
      <div class="metric"><div class="label">说明</div><div class="value" style="font-size:14px">${escapeHtml(softenAnswerText(gate.reason || "—", []))}</div></div>
      <div class="metric"><div class="label">状态</div><div class="value" style="font-size:14px">${res.ok ? "完成" : "异常"}</div></div>`;
  } else if (titles.length) {
    el.board.innerHTML =
      `<div class="metric"><div class="label">参考资料</div><div class="value">${titles.length}</div></div>` +
      `<div class="cite-list" role="list">${titles
        .map((t) => `<span class="cite-item" role="listitem">《${escapeHtml(t)}》</span>`)
        .join("")}</div>`;
  }

  // 业务侧不展示底层步骤码
  el.steps.innerHTML = "";
}

async function runFeature() {
  const f = state.currentFeature;
  if (!f?.demo_ready) return;
  let input;
  try {
    input = collectInput();
  } catch (e) {
    el.status.textContent = e.message || String(e);
    el.status.className = "status-line err";
    return;
  }
  el.runBtn.disabled = true;
  el.status.textContent = "试用中…";
  el.status.className = "status-line";
  try {
    const resp = await fetch(runEndpointFor(f), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        feature_id: f.feature_id,
        skill_id: f.skill_id,
        department_id: f.department_id,
        input,
        options: { return_steps: true },
      }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || JSON.stringify(data));
    renderResult(data);
  } catch (e) {
    el.status.textContent = `未能完成：${e.message || e}`;
    el.status.className = "status-line err";
  } finally {
    el.runBtn.disabled = false;
  }
}

async function openGuideStep(departmentId, featureId) {
  state.departmentId = departmentId;
  state.selectedId = featureId;
  await loadFeatures();
}

async function loadFeatures() {
  syncUrl();
  renderDeptNav();
  const params = new URLSearchParams({ department_id: state.departmentId });
  const [featResp, flowResp] = await Promise.all([
    fetch(`/v1/features?${params}`),
    fetch(`/v1/flows?${params}`),
  ]);
  const featData = await featResp.json();
  const flowData = await flowResp.json();
  if (!featResp.ok) throw new Error(featData.detail || "功能列表加载失败");
  state.features = featData.features || [];
  state.flows = flowResp.ok ? flowData.flows || [] : [];

  // 选中项若不属于当前部门则清空（指南除外）
  if (
    state.selectedId &&
    state.selectedId !== "__guide__" &&
    !state.features.find((f) => f.feature_id === state.selectedId)
  ) {
    state.selectedId = null;
  }
  if (state.selectedId === "__guide__" && !showGuideInDept()) {
    state.selectedId = null;
  }

  renderDeptIntro();
  renderFeatureRail();
  renderMainView();
  syncUrl();
}

function bindGuideButtons() {
  document.getElementById("btn-guide-step1a")?.addEventListener("click", () => {
    openGuideStep("service", "F-SVC-001");
  });
  document.getElementById("btn-guide-step1b")?.addEventListener("click", () => {
    openGuideStep("service", "F-SVC-001-EXT");
  });
  document.getElementById("btn-guide-step2")?.addEventListener("click", () => {
    openGuideStep("user_ops", "F-UO-017");
  });
}

async function boot() {
  const resp = await fetch("/v1/departments");
  const data = await resp.json();
  state.departments = data.departments || [];
  if (!state.departments.find((d) => d.department_id === state.departmentId)) {
    state.departmentId = state.departments[0]?.department_id || "service";
  }
  await loadFeatures();
  bindGuideButtons();
  el.runBtn.addEventListener("click", runFeature);
  el.sampleBtn.addEventListener("click", fillSample);
  el.closeBtn.addEventListener("click", () => {
    el.runner.hidden = true;
    el.closeBtn.hidden = true;
  });
}

boot().catch((e) => {
  if (el.railSub) el.railSub.textContent = `初始化失败：${e.message || e}`;
});
