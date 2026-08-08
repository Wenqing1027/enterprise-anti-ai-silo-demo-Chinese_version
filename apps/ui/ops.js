/* IT 运维看板：健康分 · 四大黄金指标 · 事件关联 · 根因 · 分环子页 · 调用链 */

const qs = new URLSearchParams(location.search);
const isEmbed =
  location.pathname.endsWith("/ops/embed") || qs.get("embed") === "1";
if (isEmbed) document.body.classList.add("embed", "ops-embed");

const LOOPS = [
  { id: "platform", title: "全局看板", blurb: "平台健康与黄金指标" },
  { id: "retrieve", title: "Retrieve", blurb: "检索环运维" },
  { id: "act", title: "Act", blurb: "行动环运维" },
  { id: "extract", title: "Extract", blurb: "抽取环运维" },
  { id: "plan", title: "Plan", blurb: "规划环运维" },
];

const VALID_SCOPES = new Set(LOOPS.map((l) => l.id));
function resolveScope() {
  const raw = qs.get("loop") || "";
  // 旧 URL ?view=traces 不是环 id，忽略，避免误请求 /v1/ops/loops/traces
  return VALID_SCOPES.has(raw) ? raw : "platform";
}

const state = {
  scope: resolveScope(),
  dash: null,
  trace: null,
};

const el = {
  nav: document.getElementById("ops-nav"),
  panel: document.getElementById("ops-panel"),
  refresh: document.getElementById("btn-refresh"),
};

function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function syncUrl() {
  const u = new URL(location.href);
  u.searchParams.set("loop", state.scope);
  u.searchParams.delete("view");
  u.searchParams.delete("agent_type");
  if (state.trace?.run_id) u.searchParams.set("run_id", state.trace.run_id);
  else u.searchParams.delete("run_id");
  history.replaceState(null, "", u);
}

function renderNav() {
  el.nav.innerHTML = LOOPS.map((v) => {
    const active = v.id === state.scope ? "active" : "";
    return `<button type="button" class="side-item ${active}" data-scope="${v.id}">
      <span class="side-item-title">${escapeHtml(v.title)}</span>
      <span class="side-item-meta">${escapeHtml(v.blurb)}</span>
    </button>`;
  }).join("");
  el.nav.querySelectorAll("[data-scope]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      state.scope = btn.dataset.scope;
      state.trace = null;
      await loadDash();
      render();
    });
  });
}

async function loadDash() {
  const url =
    state.scope === "platform"
      ? "/v1/ops/overview"
      : `/v1/ops/loops/${encodeURIComponent(state.scope)}`;
  const r = await fetch(url);
  if (!r.ok) {
    const body = await r.text().catch(() => "");
    throw new Error(`HTTP ${r.status} ${url}${body ? " · " + body.slice(0, 120) : ""}`);
  }
  state.dash = await r.json();
}

/** SVG 折线（无第三方图库，保持清爽） */
function sparkline(points, opts = {}) {
  const w = opts.w || 280;
  const h = opts.h || 72;
  const pad = 6;
  const vals = (points || []).map((p) => Number(p.value) || 0);
  if (!vals.length) {
    return {
      last: null,
      svg: `<svg class="ops-spark" viewBox="0 0 ${w} ${h}" width="100%" height="${h}"></svg>`,
    };
  }
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const span = max - min || 1;
  const coords = vals.map((v, i) => {
    const x = pad + (i * (w - pad * 2)) / Math.max(1, vals.length - 1);
    const y = h - pad - ((v - min) / span) * (h - pad * 2);
    return [x, y];
  });
  const d = coords.map((c, i) => `${i ? "L" : "M"}${c[0].toFixed(1)},${c[1].toFixed(1)}`).join(" ");
  const area =
    `${d} L${coords[coords.length - 1][0].toFixed(1)},${h - pad} L${coords[0][0].toFixed(1)},${h - pad} Z`;
  const last = vals[vals.length - 1];
  const hlTs = opts.highlightTs;
  let hlCircle = "";
  if (hlTs && points) {
    const idx = points.findIndex((p) => p.ts === hlTs);
    if (idx >= 0 && coords[idx]) {
      hlCircle = `<circle cx="${coords[idx][0].toFixed(1)}" cy="${coords[idx][1].toFixed(1)}" r="4" fill="var(--danger)" />`;
    }
  }
  return {
    last,
    svg: `<svg class="ops-spark" viewBox="0 0 ${w} ${h}" width="100%" height="${h}" preserveAspectRatio="none" aria-hidden="true">
    <path d="${area}" fill="var(--accent-soft)" opacity="0.7"></path>
    <path d="${d}" fill="none" stroke="var(--accent)" stroke-width="2"></path>
    ${hlCircle}
  </svg>`,
  };
}

function healthBlock(h) {
  const level = h?.level || "good";
  const score = h?.score ?? "—";
  return `<div class="ops-health ops-health-${escapeHtml(level)}">
    <div class="ops-health-label">全局健康分</div>
    <div class="ops-health-score">${escapeHtml(String(score))}<span class="ops-health-unit">分</span></div>
    <div class="ops-health-meta">成功率 ${escapeHtml(String(h?.success_rate_now ?? "—"))}% · RT ${escapeHtml(String(h?.latency_ms_now ?? "—"))} ms</div>
  </div>`;
}

function formatMetricValue(v, unit) {
  if (v == null || Number.isNaN(Number(v))) return "—";
  const n = Number(v);
  const text =
    unit === "%" || unit === "ms" || Number.isInteger(n)
      ? (Math.round(n * 100) / 100).toString()
      : n.toFixed(2);
  return text;
}

function goldenGrid(signals, highlightTs) {
  const order = [
    ["success_rate", "成功率"],
    ["latency_ms", "RT 响应时间"],
    ["throughput", "吞吐量"],
    ["error_count", "错误数"],
  ];
  return `<div class="ops-golden">
    ${order
      .map(([key, fallback]) => {
        const s = signals?.[key] || {};
        const pts = s.points || [];
        const label = s.label || fallback;
        const unit = s.unit || "";
        const spark = sparkline(pts, { highlightTs });
        const value =
          s.value != null
            ? s.value
            : spark.last != null
              ? spark.last
              : pts.length
                ? pts[pts.length - 1].value
                : null;
        return `<div class="ops-golden-card">
          <div class="ops-golden-head">
            <strong>${escapeHtml(label)}</strong>
            <span class="pill pill-ghost">${escapeHtml(unit)}</span>
          </div>
          <div class="ops-golden-body">
            <div class="ops-golden-value">${escapeHtml(formatMetricValue(value, unit))}<span class="ops-golden-unit">${escapeHtml(unit)}</span></div>
            <div class="ops-golden-chart">${spark.svg || spark}</div>
          </div>
        </div>`;
      })
      .join("")}
  </div>`;
}

function eventsPanel(events, highlightTs) {
  const rows = events || [];
  return `<div class="ops-events ${highlightTs ? "ops-events-alert" : ""}">
    <div class="ops-events-head">
      <strong>事件 / 变更</strong>
      ${highlightTs ? '<span class="pill pill-warn">告警：变更后指标变差</span>' : '<span class="pill pill-ghost">巡检</span>'}
    </div>
    <p class="card-note">变更本身不是告警；「变更后指标变差」才是。列表用影响范围说明因果。</p>
    <ul class="ops-event-list">
      ${
        rows
          .map((e) => {
            const corr = e.correlate ? "corr" : "";
            const lvl = e.impact_level || "info";
            const kindWarn = e.kind === "alert" || e.kind === "error" || e.kind === "warn";
            return `<li class="ops-event ${corr} impact-${escapeHtml(lvl)}">
              <div class="ops-event-top">
                <span class="pill ${kindWarn ? "pill-warn" : "pill-ghost"}">${escapeHtml(e.kind || "event")}</span>
                <time>${escapeHtml((e.ts || "").replace("T", " ").slice(0, 19))}</time>
              </div>
              <div class="ops-event-title">${escapeHtml(e.title || "")}</div>
              <div class="ops-event-detail">${escapeHtml(e.detail || "")}</div>
              ${
                e.impact_scope || e.impact
                  ? `<div class="ops-impact">影响：${escapeHtml(e.impact_scope || "—")}${
                      e.impact ? ` · ${escapeHtml(e.impact)}` : ""
                    }</div>`
                  : ""
              }
              ${e.run_id ? `<button type="button" class="ghost mini" data-run="${escapeHtml(e.run_id)}">打开调用链</button>` : ""}
            </li>`;
          })
          .join("") || '<li class="card-note">暂无事件</li>'
      }
    </ul>
  </div>`;
}

function rcaCard(rca) {
  if (!rca) return "";
  const evidence = (rca.evidence || [])
    .map((x, i) => `<li><span class="ops-ev-n">${i + 1}</span><span>${escapeHtml(x)}</span></li>`)
    .join("");
  const q = rca.log_query || {};
  return `<div class="ops-rca">
    <div class="ops-rca-head"><strong>${escapeHtml(rca.title || "根因分析")}</strong>
      <span class="pill pill-ok">规则引擎 · 置信 ${(Number(rca.confidence || 0) * 100).toFixed(0)}%</span>
    </div>
    <div class="ops-rca-grid">
      <p class="ops-rca-chain"><b>根因推断：</b>${escapeHtml(rca.summary || "")}</p>
      <p><b>怀疑：</b>${escapeHtml(rca.suspect || "")}</p>
      <p><b>建议：</b>${escapeHtml(rca.suggestion || "")}</p>
    </div>
    ${evidence ? `<ul class="ops-evidence">${evidence}</ul>` : ""}
    <div class="ops-rca-actions">
      <button type="button" class="primary mini" id="btn-error-logs"
        data-q="${escapeHtml(q.q || "")}"
        data-status="${escapeHtml(q.status || "error")}"
        data-runs="${escapeHtml((q.run_ids || rca.related_run_ids || []).join(","))}">查看相关错误日志</button>
      ${(rca.related_run_ids || [])
        .slice(0, 3)
        .map(
          (id) =>
            `<button type="button" class="ghost mini" data-run="${escapeHtml(id)}">${escapeHtml(id)}</button>`
        )
        .join(" ")}
    </div>
    <div id="ops-log-box" class="ops-log-box" hidden></div>
  </div>`;
}

function loopCards(cards) {
  if (state.scope !== "platform" || !cards?.length) return "";
  return `<div class="ops-loop-cards">
    ${cards
      .map((c) => {
        const rate = c.success_rate == null ? "—" : c.success_rate + "%";
        return `<button type="button" class="ops-loop-card" data-scope="${escapeHtml(c.control_loop)}">
          <div class="ops-loop-name">${escapeHtml(c.name || c.control_loop)}</div>
          <div class="ops-loop-meta">runs ${c.runs ?? 0} · 成功率 ${escapeHtml(String(rate))}</div>
          <div class="card-note">进入子页查看该环指标与调用链 →</div>
        </button>`;
      })
      .join("")}
  </div>`;
}

function callChainHtml(chain) {
  if (!chain?.nodes?.length) return `<p class="card-note">无调用链节点</p>`;
  const sev = chain.severity || (chain.ok === false ? "error" : chain.slow ? "slow" : chain.blocked ? "blocked" : "ok");
  const nodes = chain.nodes
    .map((n) => {
      const st = n.status ? statusDot(n.status) : "";
      const nSev =
        String(n.status || "").toLowerCase().match(/err|fail/)
          ? "error"
          : String(n.status || "").toLowerCase() === "warn"
            ? "slow"
            : "";
      return `<div class="ops-chain-node ops-chain-${escapeHtml(n.kind || "step")} ${nSev ? "ops-node-" + nSev : ""}">
        <div class="ops-chain-label">${escapeHtml(n.label)}${st}</div>
      </div>`;
    })
    .join('<div class="ops-chain-arrow">→</div>');
  const badge =
    sev === "error"
      ? '<span class="pill" style="color:var(--danger)">报错</span>'
      : sev === "slow"
        ? '<span class="pill pill-warn">慢调用</span>'
        : sev === "blocked"
          ? '<span class="pill pill-warn">闸门阻断</span>'
          : '<span class="pill pill-ok">ok</span>';
  return `<div class="ops-chain ops-sev-${escapeHtml(sev)}">
    <div class="ops-chain-meta">
      <code>${escapeHtml(chain.run_id)}</code>
      · ${escapeHtml(chain.control_loop || "—")}
      · ${escapeHtml(String(chain.duration_ms ?? "—"))} ms
      ${chain.demo ? '<span class="pill pill-ghost">排障样例</span>' : ""}
      ${badge}
    </div>
    <div class="ops-chain-flow">${nodes}</div>
  </div>`;
}

function statusDot(st) {
  const s = String(st).toLowerCase();
  if (s.includes("err") || s.includes("fail")) return ' <span class="pill" style="color:var(--danger)">err</span>';
  if (s === "warn" || s.includes("slow")) return ' <span class="pill pill-warn">slow</span>';
  return "";
}

function runsAndChains(dash) {
  const runs = dash.runs || [];
  const chains = dash.call_chains || [];
  return `<div class="ops-trace-block">
    <h3 class="ops-h3">调用链</h3>
    <p class="card-note">优先展示报错 / 慢调用现场；一次 Skill 运行 = 一条链路（入口 → Skill → 步骤）。</p>
    ${chains.map(callChainHtml).join("") || '<p class="card-note">暂无链路。请先在业务墙跑 Demo。</p>'}
    <h3 class="ops-h3">近期 Run</h3>
    <div class="table-wrap"><table class="ops-table">
      <thead><tr><th>run_id</th><th>环</th><th>skills</th><th>耗时</th><th>状态</th><th></th></tr></thead>
      <tbody>
        ${
          runs
            .map((r) => {
              let st;
              if (r.errors || r.ok === false)
                st = '<span class="pill" style="color:var(--danger)">error</span>';
              else if (r.slow)
                st = '<span class="pill pill-warn">slow</span>';
              else if (r.blocked)
                st = '<span class="pill pill-warn">blocked</span>';
              else st = '<span class="pill pill-ok">ok</span>';
              return `<tr>
                <td><code>${escapeHtml(r.run_id)}</code>${r.demo ? ' <span class="pill pill-ghost">样例</span>' : ""}</td>
                <td>${escapeHtml(r.control_loop || "—")}</td>
                <td>${escapeHtml((r.skills || []).join(", ") || "—")}</td>
                <td>${escapeHtml(String(r.duration_ms ?? "—"))}</td>
                <td>${st}</td>
                <td><button type="button" class="primary mini" data-run="${escapeHtml(r.run_id)}">链路</button></td>
              </tr>`;
            })
            .join("") || `<tr><td colspan="6">暂无</td></tr>`
        }
      </tbody>
    </table></div>
    <div id="trace-box"></div>
  </div>`;
}

function bindActions() {
  el.panel.querySelectorAll("[data-scope]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      state.scope = btn.dataset.scope;
      state.trace = null;
      await loadDash();
      render();
    });
  });
  el.panel.querySelectorAll("[data-run]").forEach((btn) => {
    btn.addEventListener("click", () => openTrace(btn.dataset.run));
  });
  const logBtn = document.getElementById("btn-error-logs");
  if (logBtn) {
    logBtn.addEventListener("click", () =>
      openErrorLogs({
        q: logBtn.dataset.q || "",
        status: logBtn.dataset.status || "error",
        runs: (logBtn.dataset.runs || "").split(",").filter(Boolean),
      })
    );
  }
}

async function openErrorLogs({ q, status, runs }) {
  const box = document.getElementById("ops-log-box");
  if (!box) return;
  box.hidden = false;
  box.innerHTML = `<p class="blurb">加载错误日志…</p>`;
  try {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (q) params.set("q", q);
    params.set("limit", "40");
    const [storeLogs, ...traces] = await Promise.all([
      fetch(`/v1/ops/logs?${params}`).then((r) => r.json()),
      ...runs.slice(0, 3).map((id) =>
        fetch(`/v1/ops/runs/${encodeURIComponent(id)}`).then((r) => r.json())
      ),
    ]);
    const rows = [];
    for (const t of traces) {
      if (!t.found) continue;
      for (const s of t.steps || []) {
        const d = s.detail || {};
        const st = String(s.step_status || "").toLowerCase();
        if (!(st.includes("err") || st === "warn" || d.error || d.error_code)) continue;
        rows.push({
          ts: s.step_ts,
          run_id: t.run_id,
          step_name: s.step_name,
          step_status: s.step_status,
          detail: d,
          source: t.summary?.demo ? "排障样例" : "run",
        });
      }
    }
    for (const x of storeLogs.logs || []) {
      rows.push({
        ts: x.step_ts,
        run_id: x.run_id,
        step_name: x.step_name,
        step_status: x.step_status,
        detail: x.detail || {},
        source: "store",
      });
    }
    if (!rows.length) {
      box.innerHTML =
        '<p class="card-note">暂无匹配日志。可打开上方报错/慢调用链路查看步骤现场。</p>';
      return;
    }
    box.innerHTML = `<h3 class="ops-h3">相关错误日志</h3>
      <ul class="ops-list">${rows
        .slice(0, 24)
        .map((r) => {
          const d = r.detail || {};
          const msg = d.error || d.message || d.error_code || "";
          return `<li><code>${escapeHtml(r.run_id || "")}</code>
            · ${escapeHtml((r.ts || "").replace("T", " ").slice(0, 19))}
            · <b>${escapeHtml(r.step_name || "")}</b>
            · <span class="pill ${String(r.step_status).includes("err") ? "" : "pill-warn"}" ${
              String(r.step_status).includes("err") ? 'style="color:var(--danger)"' : ""
            }>${escapeHtml(r.step_status || "")}</span>
            ${d.tool ? ` · tool=<code>${escapeHtml(d.tool)}</code>` : ""}
            ${msg ? ` · ${escapeHtml(String(msg))}` : ""}
            ${r.source === "排障样例" ? ' <span class="pill pill-ghost">样例</span>' : ""}
          </li>`;
        })
        .join("")}</ul>`;
    box.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (e) {
    box.innerHTML = `<p class="status-line err">${escapeHtml(e.message || e)}</p>`;
  }
}

async function openTrace(runId) {
  const box = document.getElementById("trace-box");
  if (!box) return;
  box.innerHTML = `<p class="blurb">加载调用链 ${escapeHtml(runId)}…</p>`;
  try {
    const data = await fetch(`/v1/ops/runs/${encodeURIComponent(runId)}`).then((r) => r.json());
    state.trace = data;
    syncUrl();
    if (!data.found) {
      box.innerHTML = `<p class="status-line err">未找到 run</p>`;
      return;
    }
    const steps = data.steps || [];
    box.innerHTML = `
      <h3 class="ops-h3">链路详情</h3>
      ${callChainHtml(data.call_chain)}
      <ul class="ops-list">
        ${steps
          .map((s) => {
            const d = s.detail || {};
            const bad = String(s.step_status || "").toLowerCase().match(/err|fail|warn/);
            return `<li class="${bad ? "ops-step-bad" : ""}">${escapeHtml((s.step_ts || "").replace("T", " ").slice(0, 19))}
              · <code>${escapeHtml(s.step_name)}</code>
              · ${escapeHtml(s.step_status)}
              ${d.tool ? " · tool=<code>" + escapeHtml(d.tool) + "</code>" : ""}
              ${d.error_code ? " · " + escapeHtml(d.error_code) : ""}
              ${d.error ? " · " + escapeHtml(d.error) : ""}
              ${d.message ? " · " + escapeHtml(d.message) : ""}
              ${d.latency_ms != null ? " · " + escapeHtml(String(d.latency_ms)) + "ms" : ""}
              ${d.stop_reason ? " · " + escapeHtml(d.stop_reason) : ""}</li>`;
          })
          .join("")}
      </ul>
    `;
    box.scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (e) {
    box.innerHTML = `<p class="status-line err">${escapeHtml(e.message || e)}</p>`;
  }
}

function render() {
  syncUrl();
  renderNav();
  const dash = state.dash || {};
  const scopeTitle =
    LOOPS.find((l) => l.id === state.scope)?.title || state.scope;
  const hl = dash.highlight_ts;
  el.panel.innerHTML = `
    <div class="ops-dash-head">
      <div>
        <div class="hero-chip">${state.scope === "platform" ? "平台全局" : "控制环子页"}</div>
        <h2>${escapeHtml(scopeTitle)}</h2>
        <p class="blurb">四大黄金指标实时曲线；异常时旁侧事件高亮；下方为调用链（平台核心运行证据）。</p>
      </div>
      ${healthBlock(dash.health)}
    </div>
    ${goldenGrid(dash.golden_signals, hl)}
    <div class="ops-mid">
      ${eventsPanel(dash.events, hl)}
      ${rcaCard(dash.root_cause)}
    </div>
    ${loopCards(dash.loop_cards)}
    ${runsAndChains(dash)}
  `;
  bindActions();
  const rid = qs.get("run_id");
  if (rid) openTrace(rid);
}

async function boot() {
  try {
    if (!LOOPS.some((l) => l.id === state.scope)) state.scope = "platform";
    await loadDash();
    render();
  } catch (e) {
    el.panel.innerHTML = `<p class="status-line err">初始化失败：${escapeHtml(e.message || e)}</p>`;
  }
  el.refresh?.addEventListener("click", async () => {
    el.panel.innerHTML = `<p class="blurb">刷新中…</p>`;
    await loadDash();
    render();
  });
}

boot();
