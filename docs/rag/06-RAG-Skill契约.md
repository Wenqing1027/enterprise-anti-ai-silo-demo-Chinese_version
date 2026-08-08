# RAG · Skill 契约（R3）

> **喂食核心 · RAG R3**  
> 控制环仍为 planned（R4）；本步交付可加载的 `skill.yaml` + Pydantic schema + 分流  
> 版本：V1.0 · 2026-08-05

---

## 1. 定位

| 项 | 说明 |
|----|------|
| 做什么 | 定义 RAG Skill 机读契约，挂 `repair_kb` / `policy_kb` / `hr_rules` |
| 不做什么 | 不实现 `retrieve→stuff→generate` 运行时（属 R4） |
| 与 R2 关系 | Skill 声明 `kb_domains_allow`；检索仍走已接通的 `search_kb` / TF-IDF |

---

## 2. 识别与分流

```text
payload_schema?     → Extraction
agent_type: rag     → RAG
否则                → ReAct
```

实现：`apps/skill_dispatch.peek_skill_kind` / `load_skill_public`。

---

## 3. 一期三个 Skill

| skill_id | 域 | 部门 | 对齐功能 |
|----------|-----|------|----------|
| `repair_kb` | repair | 服务 | F-SVC-002/004 · F-UO-009 |
| `policy_kb` | policy | 订单/政策 | 政策口径问答 |
| `hr_rules` | hr | 人资 | F-HR-001/003 |

路径：

- `skills/repair_kb/skill.yaml`
- `skills/policy_kb/skill.yaml`
- `skills/hr_rules/skill.yaml`
- Schema：`agents/rag/skill_schema.py`
- Loader：`agents/rag/skill_loader.py`

---

## 4. 关键字段

| 字段 | 必填 | 说明 |
|------|------|------|
| `agent_type` | ✅ | `rag` |
| `kb_domains_allow` | ✅ | 非空；与 `security.kb_domains_allow` 双闸 |
| `top_k` | | 默认 5 |
| `max_context_chars` | | stuff 预算，默认 2400 |
| `cite_required` | | 终答须引用 |
| `success_when` | | `cited_answer` |
| `allowed_tools` | | catalog / 文档；环内直接 DataFetcher |
| `tone` / `system_extra` / `output_format` | | Prompt 槽（R4 消费） |

Prompt 段序常量：`RAG_PROMPT_SECTION_ORDER`（A_base…F_security）。

---

## 5. 验收

```bash
python -c "
from apps.skill_dispatch import peek_skill_kind, load_skill_public, list_skill_ids
assert peek_skill_kind('repair_kb')=='rag'
assert peek_skill_kind('policy_kb')=='rag'
assert peek_skill_kind('hr_rules')=='rag'
assert peek_skill_kind('fill_ticket')=='react'
assert peek_skill_kind('ticket_fields')=='extraction'
for sid in ('repair_kb','policy_kb','hr_rules'):
    p=load_skill_public(sid)
    assert p['agent_kind']=='rag' and p['kb_domains_allow']
print('skills', [s for s in list_skill_ids() if peek_skill_kind(s)=='rag'])
"
python scripts/smoke_rag_skills.py
```

---

## 6. 下一步

**R4 控制环** ✅ — 见 [07-控制环实现与接通](./07-控制环实现与接通.md)。

下一可选：**R5 金标评测集** / Catalog UI 细调。
