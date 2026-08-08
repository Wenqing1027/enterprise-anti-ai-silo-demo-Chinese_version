# 界面原则 + 集成 API（业务墙 / 运维排查）

> **版本**：V2.0 · 2026-08-07  
> **纠偏**：运维台 **不是**「按控制环试跑 Skill / 查规章」；那是业务墙职责。  
> 运维台 = **故障排查**：日志流 · 监控指标 · 链路（run）数据。

---

## 1. 双页面

| 页面 | 路由 | 受众 | 原则 |
|------|------|------|------|
| 业务工作台 | `/business` | 各部门业务角色 | 一卡一功能一 Skill；平台环 + 部门 Skill；可试跑 Demo |
| 运维控制台 | `/ops`、`/ops/embed` | 技术运维 / SRE | 运行态排查：日志 / 指标 / 链路 / 共享产出健康 |

```text
业务：选部门 → 功能卡片 → 试跑本 Skill（POST /v1/{loop}/runs 或 /v1/runs）

运维：总览指标 → 日志流过滤 → 按 run_id 看链路 → 查 AIOutput / 工具健康
      （不提供业务 Skill 试跑入口）
```

---

## 2. 运维台数据源（Demo）

| 面板 | 来源 |
|------|------|
| 指标 | `SharedStore.stats` + 步骤错误率 + 四环就绪状态 |
| 日志流 | `run_logs.json`（`list_run_logs`） |
| 链路 | 按 `run_id` 聚合步骤 + 关联 `AIOutput` |
| 共享产出 | `GET /v1/ai-outputs` |
| 工具健康 | `GET /v1/tools` + registry 计数 |

API（运维专用）：

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/v1/ops/overview` | 全局：健康分 · 四大黄金指标 · 事件 · 根因 · 调用链 |
| GET | `/v1/ops/loops/{control_loop}` | **四环子页**同形数据 |
| GET | `/v1/ops/logs` | 日志流 |
| GET | `/v1/ops/runs` | 近期 run 列表 |
| GET | `/v1/ops/runs/{run_id}` | 单次**调用链** + 步骤 + AIOutput |

---

## 3. 业务可跑（仍在业务墙）

见业务墙卡片与 `docs/agent-orchestration.md`；运维台不再挂 RAG/填单试跑器。

---

## 4. 启动

```bash
bash scripts/ensure_api.sh
# 业务 http://127.0.0.1:8000/business
# 运维排查 http://127.0.0.1:8000/ops
# 嵌入 http://127.0.0.1:8000/ops/embed
```
