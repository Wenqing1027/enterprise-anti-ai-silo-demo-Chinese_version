# Planning · 模块三：机读契约与 catalog 对接

> **喂食核心 · 模块三**  
> 真相源：`data/entities/department_flows.json`（手工维护；生成脚本不覆盖）  
> Skill 归属环：`apps/skill_loops.py` · `data/entities/skill_loop_map.json`  
> 暴露：`apps/catalog.py` · `GET /v1/flows` · `GET /v1/departments/{id}/flows`  
> 版本：V2.1 · 2026-08-07

---

## 1. JSON 顶层

```json
{
  "version": "v2",
  "description": "…节点 = 可独立运行的 Skill/功能…",
  "node_kinds": ["skill", "placeholder", "store_read", "store_write"],
  "control_loops": ["retrieve", "act", "extract", "plan"],
  "flows": [ /* Flow 对象 */ ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `version` | string | 契约版本，当前 `v2` |
| `flows` | array | 部门内功能关系流 |

---

## 2. Flow 对象

| 字段 | 必填 | 说明 |
|------|------|------|
| `flow_id` | ✅ | 全局唯一 |
| `department_id` | ✅ | 对齐 `apps.catalog.DEPARTMENTS` |
| `name` | ✅ | 人读名称 |
| `demo_ready` | ✅ | 是否对齐 Demo Story |
| `nodes` | ✅ | 节点列表 |
| `edges` | ✅ | 边列表（可空） |
| `parallel_groups` | ✅ | 并行组（可空） |
| `feature_ids` | | 关联业务功能 ID |
| `notes` | | 人读备注 |

---

## 3. Node（功能关系说明书口径）

**节点 = 可独立运行的一个功能 Skill**（或共享层读写点 / 占位），**不是**「Agent 管道里的一步」。

| 字段 | 说明 |
|------|------|
| `node_id` | 流内唯一 |
| `kind` | `skill` · `placeholder` · `store_read` · `store_write` |
| `skill_id` | 可空；`skill` / 部分 `placeholder` 必填意图 |
| `control_loop` | `retrieve` \| `act` \| `extract` \| `plan`（store_* 为 null） |
| `label` | 人读短名 |
| `extension_type` | 可选：`rule_llm` / `vision`（归入父环后保留） |
| `note` | 可选说明 |

> 兼容：catalog 加载时若仍见旧 `kind: agent_type` / `agent_type: rag`，会规范为 `kind: skill` + `control_loop`。

---

## 4. Edge

| 字段 | 说明 |
|------|------|
| `from` · `to` | `node_id` |
| `mode` | `sequence` = **数据依赖**（通常经共享层，两次独立运行）；`parallel` = 可独立演示 |
| `via` | 共享契约：`AIOutput` · `tag_id:…` · `payload_schema:…` |

**不是** Extract Agent 做完把话筒交给 Act Agent。

---

## 5. Parallel group

```json
{ "group_id": "pg_prep", "node_ids": ["n1", "n2"], "label": "并行可选功能" }
```

---

## 6. Skill 归属环

| 层 | 映射 |
|----|------|
| `skill.yaml` | 真字段 `control_loop:`（retrieve\|act\|extract\|plan）；RAG 另保留 `agent_type: rag` 供 loader |
| 台账 | `apps/skill_loops.py` · `data/entities/skill_loop_map.json` |
| 公开 API | `GET /v1/skills` → 每条含 `control_loop` |
| flows 节点 | `control_loop` 与 skill 台账一致 |
| FEATURES | `agent_type` 已用规范环名（与 control_loop 同口径） |

一期已落地：

| control_loop | skill_id |
|--------------|----------|
| retrieve | `repair_kb` · `policy_kb` · `hr_rules` |
| act | `fill_ticket` · `crm_lookup` · `channel_ops` · `shared_write` |
| extract | `ticket_fields` · `voc_entities` · `voc_tagging` |
| plan | `renewal_plan`（Story2 / user_ops_renewal_gate） |

`# flow: <flow_id>` 注释仍用于引用编排流。

### 运行 API（B3）

| 入口 | 说明 |
|------|------|
| `POST /v1/planning/runs` | Plan 专用（UI / 运维主路径） |
| `POST /v1/runs` | 统一入口：`control_loop=plan`（或 `agent_type=planning` / 由 feature·skill 推断） |
| `GET /v1/planning/runs/{run_id}` | 回看步骤日志 |

机读：`/v1/meta` → `unified_runs_api`、`legacy_api_paths.plan`；`data/entities/control_loop_aliases.json`。

四环运行响应统一为 **RunResult**（阶段 D）：见 [docs/run-result.md](../run-result.md)；`GET /v1/meta` → `run_result`。

---

## 7. 维护约定

- **手工维护** `department_flows.json`  
- `scripts/generate_synthetic_data.py` **不得**覆盖该文件  
- 新增 Skill：同步 `control_loop` 字段 + `skill_loops.py` + 相关 flow 节点  

---

## 8. 验收速查

```bash
python3 -c "
from apps.catalog import list_flows, get_flow
from apps.skill_dispatch import load_skill_public
from apps.skill_loops import SKILL_CONTROL_LOOPS

fs = list_flows()
assert any(f['flow_id']=='service_ticket_to_shared' and f['demo_ready'] for f in fs)
n = get_flow('service_ticket_to_shared')['nodes'][0]
assert n['kind']=='skill' and n['control_loop'] in {'retrieve','act','extract','plan'}
assert load_skill_public('fill_ticket')['control_loop']=='act'
assert len(SKILL_CONTROL_LOOPS)==10
print('A3 OK', 'flows', len(fs))
"
```
