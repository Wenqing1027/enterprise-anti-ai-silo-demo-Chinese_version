# skill.yaml 格式契约

本仓库存在 **四类** Skill YAML（对应平台四环）：

| 类型 | 识别 | 归属环 `control_loop` | 加载器 |
|------|------|------------------------|--------|
| **Act（ReAct）** | 有 `allowed_tools`，无 `payload_schema`，非 Retrieve/Plan | `act` | `agents/react/skill_loader.py` |
| **Extract** | 有 `payload_schema` | `extract` | `agents/extraction/skill_loader.py` |
| **Retrieve（RAG）** | `control_loop: retrieve` 或 `agent_type: rag` + `kb_domains_allow` | `retrieve` | `agents/rag/skill_loader.py` |
| **Plan** | `control_loop: plan` 或 `agent_type: planning` | `plan` | `agents/planning/skill_loader.py` |

分流：`apps/skill_dispatch.py`（`peek_skill_kind`）。  
归属台账：`apps/skill_loops.py` · `data/entities/skill_loop_map.json`。

---

## 公共字段（三类均有）

| 字段 | 必填 | 说明 |
|------|------|------|
| `skill_id` | ✅ | 须与目录名一致 |
| `control_loop` | ✅（建议） | `retrieve` \| `act` \| `extract` \| `plan`；缺省时由加载器/台账推断 |

---

## ReAct（Act）字段

唯一实现：`agents/react/skill_schema.py` → `SkillConfig`（加载时 Pydantic 校验）。

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `skill_id` | ✅ | string | 须与目录名一致 |
| `control_loop` | | `act` | 平台归属环 |
| `department` | | string | 部门叙事 |
| `goal` | ✅ | string | 一句话任务目标 |
| `success_hint` | | string | 给人看的成功标准 |
| `success_when` | | enum | `wrote_ai_output` / `master_lookup` / `channel_lookup` / `none` |
| `max_steps` | | int 1–32 | 工具步上限（默认 8） |
| `tone.label` / `tone.style` | ✅ | string | 风格 |
| `tone.forbid` | | string | 禁用项 |
| `allowed_tools` | ✅ | string[] | 工具白名单 |
| `system_extra` / `output_format` | | string | Prompt 补充 |
| `security` | | object | 安全槽 |

### `security` 子字段

| 字段 | 默认 | 说明 |
|------|------|------|
| `kb_domains_allow` | `[]` | 非空则限制 `search_kb.domain` |
| `max_tool_calls_per_step` | `6` | 单轮 tool_calls 上限 |
| `redact_pii_in_observation` | `true` | 回灌前脱敏 |
| `block_on_outreach` | `false` | 触达阻断硬停 |
| `prompt_forbid_extra` | `""` | 追加禁令 |

### System Prompt 段序

`A_base` → `B_tone` → `C_goal` → `C2_system_extra` → `D_tools` → `E_output` → `F_security`

---

## RAG（Retrieve）字段（摘要）

实现：`agents/rag/skill_schema.py` → `RagSkillConfig`。

| 字段 | 必填 | 说明 |
|------|------|------|
| `control_loop` | | 必须为 `retrieve` |
| `agent_type` | ✅ | 历史识别字段，仍为 `rag` |
| `kb_domains_allow` | ✅ | 非空域白名单 |
| `top_k` / `max_context_chars` | | 检索与装填预算 |
| `cite_required` | | 终答须带引用 |
| `success_when` | | `cited_answer` / `none` |
| `allowed_tools` | | 供 catalog |

一期：`repair_kb` · `policy_kb` · `hr_rules`。详见 [docs/rag/06](../docs/rag/06-RAG-Skill契约.md)。

---

## Extraction（Extract）字段（摘要）

| 字段 | 必填 | 说明 |
|------|------|------|
| `control_loop` | | `extract` |
| `payload_schema` | ✅ | `ticket_draft_v1` / `voc_entities_v1` |
| `write_ai_output` / `consumer_allow` | | 资产化 |

一期：`ticket_fields` · `voc_entities` · `voc_tagging`。

---

## 部门内编排（flow）— 功能关系说明书

机读真相：`data/entities/department_flows.json`（见 [docs/planning/03](../docs/planning/03-模块三-机读契约与catalog对接.md)）。

- **节点** = 可独立跑的 Skill/功能（或共享层点），**不是** Agent 管道  
- `mode: sequence` = 数据依赖（两次独立运行，经共享层）  
- `mode: parallel` = 可独立演示  

YAML 顶部注释仍可引用：`# flow: service_ticket_to_shared`。

| skill_id | control_loop | 关系 |
|----------|--------------|------|
| `fill_ticket` | act | `produces_for: [renewal_plan, voc_tagging]` |
| `ticket_fields` | extract | ∥ `fill_ticket` 同目标可选 |
| `voc_tagging` / `voc_entities` | extract | 写共享；跨部门只靠 `AIOutput` |
| `renewal_plan` | plan | Story2 / `user_ops_renewal_gate`；`consumes_from` 上游；闸门+放行短计划同次 |
| `repair_kb` | retrieve | 与 Story1 **并行存在** |
| `policy_kb` | retrieve | 与审单示意 **并行可选** |
| `hr_rules` | retrieve | 独立问答流 |
| `crm_lookup` / `channel_ops` / `shared_write` | act | 查数 / 渠道 / 共享写入 |
