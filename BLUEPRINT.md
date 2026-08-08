# Qingshu Mobility · Anti-AI-Silo 平台架构蓝图

> **用途**：求职作品集（数字化转型咨询）· GitHub + 录屏讲解  
> **定位**：参考实现 / MVP 示意，**非**客户交付、**非**生产中台  
> **品牌**：虚构智能电动车出行企业 **青枢出行（Qingshu Mobility）**  
> **版本**：V2.1 · 2026-08-07 — 明确 **一功能一 Skill**；禁止 Agent 互相对话/管道接力  

相关文档：[设计决策](./docs/design-decisions.md) · [咨询叙事](./docs/consulting-narrative.md) · [平台管什么/不管什么](./docs/shared-vs-not-shared.md) · [Planning](./docs/planning/01-模块一-背景与编排原则.md)

---

## 0. 一句话产品定义

企业 AI 转型的可治理成品是：

**平台统一管理的 Control Loops + Tools**，外加各部门自建的 **Skills**。

防 AI 孤岛的方法 **不是**「共用一个 Agent / 共用几个人设 Agent」（仍会在各部门重复造环、重复造手脚），而是：

| 平台发版与治理 | 业务部门交付 |
|----------------|--------------|
| 有限套 **控制环**（认知执行模式） | 本部门 **Skill**（目标、语气、白名单、schema/索引槽） |
| 统一 **工具台账**（按治理类型分类） | 选用平台已批准的 tools，不私建 DataFetcher |
| 共享语义 / `AIOutput` / 能力目录 | 读写共享产出，跨部门不直连私库 |

### 0.1 一功能一 Skill（运行时铁律）

| 要 | 不要 |
|----|------|
| **每种业务功能 = 一个 Skill**；一次运行只选一个 `skill_id` | 上一个 Agent 对话交给下一个 Agent |
| 该功能所需步骤在 **本 Skill 的工具白名单内** 完成 | 把「Extract 环再交给 Act 环」当成默认产品路径 |
| 另一功能若要读历史结果：另开一次运行，**读共享层** | Multi-Agent 互聊 / 自动管道联跑多 Skill |

`department_flows` 只描述 **功能之间经共享产出的可选依赖/并行关系**（说明与治理用），**不是**运行时 Agent 接力编排器。

**不是**：全公司一个万能大脑 / System Prompt。  
**不是**：按业务部门各建一套互不相通的 Agent 工程。  
**不是**：企业级单 Orchestrator 包办所有部门顺序。  
**不是**：Agent 互相对话完成跨功能协作。

---

## 1. 架构裁定（相对旧叙事）



| 轴 | 内容 |
|----|------|
| **平台 Control Loops（4）** | Retrieve · Act · Extract · Plan |
| **平台 Tools（3 类）** | Read · Knowledge · Write/Govern |
| **部门 Skills（N）** | **一功能一 Skill**；挂在某一环上；一次运行只跑一个 |
| **关系契约** | `department_flows`：功能间经共享产出的依赖/并行说明（非 Agent 管道） |

Rule+LLM、Vision：**并入 Plan（闸门子模式）与 Extract（感知/结构化子模式）** 讲解即可；代码目录可保留为扩展位，**不再**作为平台主清单的第六、第七环。

---

## 2. 逻辑分层（平台视角）

```text
┌─────────────────────────────────────────────────────────────┐
│ L1 入口（极简）                                              │
│  CLI / FastAPI：control_loop + skill_id + 输入               │
│  业务墙 `/business`：按部门聚合 Skill（业务试跑）             │
│  运维台 `/ops`：故障排查（日志流 / 指标 / 链路），非 Skill 墙 │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ L2 平台控制环（4）★ 平台发版 / 统一治理                       │
│  Retrieve(RAG) | Act(ReAct) | Extract | Plan(Planning)       │
│  每种 = 独立控制环实现；禁止各部门复制环代码                   │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ L3 Skill 层 ★ 业务部门交付物                                 │
│  目标 / 语气 / tools 白名单 / schema·index·决策槽             │
│  例：repair_kb · fill_ticket · ticket_fields · renewal_plan  │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ L4 关系说明与协作（Demo 瘦身）★                              │
│  每次运行：单一 skill_id；run_id + 步骤日志                   │
│  flows：功能间共享依赖说明；跨功能只读/写 AIOutput，禁互聊   │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ L5 平台工具层（3 类台账）★                                   │
│  Read | Knowledge | Write/Govern — 唯一 ToolRegistry          │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ L6 统一 DataFetcher ★                                        │
│  假 CRM/工单/KB/订单… 一处实现，环与 Skill 只调用不复制       │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ L7 共享资产层（反孤岛显式层）★                               │
│  统一模型 · 标签字典 · AIOutput · CapabilityCatalog           │
└─────────────────────────────────────────────────────────────┘
```


---

## 3. 四种平台控制环

| 环 ID | 目录（现仓） | 控制环要点 | 一期 Demo Skill（示例） | 状态 |
|-------|--------------|------------|-------------------------|------|
| **retrieve** | `agents/rag/` | retrieve → stuff → generate → cite | `repair_kb` · `policy_kb` · `hr_rules` | ✅ |
| **act** | `agents/react/` | think → act → observe | `fill_ticket` · `crm_lookup` · `channel_ops` | ✅ |
| **extract** | `agents/extraction/` | schema → extract → validate | `ticket_fields` · `voc_entities` · `voc_tagging` | ✅ |
| **plan** | `agents/planning/` | 读共享 → 闸门/多步计划 →（可选）触发下游 | `renewal_plan`（Story2） | ✅ |

**子模式（不单列平台环）：**

- **Rule gate** → 归 Plan（或 Act 内硬停工具，如 `check_outreach_block`）  
- **Vision** → 归 Extract 的感知输入，或二期再拆环  

API / CLI 主口径为 `retrieve` / `act` / `extract` / `plan`；历史名 `rag` / `react` / `extraction` / `planning` 经别名表兼容（见 `apps/loops.py`、`data/entities/control_loop_aliases.json`）。Skill YAML 与既有 `/v1/{rag|react|extraction}/runs` 路径暂仍用历史名。

---

## 4. 三类平台工具（治理台账）

实现仍在 `shared/tools/`（现约 48 个）；**治理展示**归为三类，替代「只按业务域罗列」的主叙事：

| 工具类 | 含义 | 现仓映射（示例） |
|--------|------|------------------|
| **read** | 主数据 / 交易 / 经营只读 | `get_customer` · `get_ticket` · `list_renewals` · 渠道/订单只读… |
| **knowledge** | 知识检索 | `search_kb` 及 KB 相关 |
| **write_govern** | 写共享、打标、触达闸门、能力目录 | `write_ai_output` · `read_ai_outputs` · `check_outreach_block` · `list_capabilities` · `log_step` |

规则：

- 所有环 **只经 ToolRegistry 调用**，禁止私有 fetcher/tool 副本  
- Skill 用 `allowed_tools`（或等价能力目录）声明子集  
- 业务域标签（service/channel…）可保留作次级索引，**主治理轴是三类**  
- 运行时映射：`shared/tools/governance.py` · 机读台账：`data/entities/tool_class_map.json` · API：`GET /v1/tools?tool_class=`

---

## 5. Skill 与组合契约

### 5.1 Skill

- 归属 **某一个** 平台控制环（`control_loop` 字段 + `apps/skill_loops.py` 台账）  
- 携带部门语气、成功条件、工具白名单、schema/索引等  
- 机读协作关系优先写在 `data/entities/department_flows.json`（节点=可独立跑 Skill）；`skill.yaml` 可用 `# flow:` 注释引用  

### 5.2 Flows（关系说明，非联跑引擎）

见 `docs/planning/`：

- 每个节点对应 **一个可独立运行的功能 Skill**（或占位）  
- `mode: sequence` — **数据依赖**：下游功能若要正确，通常需上游已写入共享层（仍是两次独立运行，不是 Agent 对话）  
- `mode: parallel` — 两功能可任选其一或分别演示，无强制先后  
- 跨部门边 **只经 L7**  

Demo 验收（两次独立 Skill 运行，中间只经 store）：

| Story | 含义 |
|-------|------|
| **Story1** | 跑 `fill_ticket` 或 `ticket_fields` → `write_ai_output` |
| **Story2** | 另跑 `renewal_plan`（Plan）→ 读共享标签 → **阻断触达** |

没有 Story2，不得声称「已演示反 AI 孤岛」。

---

## 6. 仓库落位（与实现对齐）

```text
enterprise-anti-ai-silo-demo/
├── BLUEPRINT.md                 # 本文件（V2 平台架构）
├── README.md
├── docs/
│   ├── design-decisions.md      # 设计决策（为何 4×3 等）
│   ├── consulting-narrative.md
│   ├── shared-vs-not-shared.md  # 平台管什么 / 不管什么
│   ├── planning/                # Plan 环与 flows 契约
│   ├── react|extraction|rag/    # 各环喂食文档（实现向）
│   └── agent-orchestration.md
├── shared/                      # 平台基础设施 L5–L7
│   ├── models/ · store/ · datafetcher/ · tools/
├── agents/                      # 仅控制环
│   ├── rag/ · react/ · extraction/ · planning/
│   ├── rule_llm/ · vision/      # 扩展位（非平台主清单）
├── skills/                      # 部门插件
├── data/entities/department_flows.json
└── apps/                        # CLI + API（入口）
```

---

## 7. 明确非目标

- ❌ Multi-Agent 互相聊天编排  
- ❌ 真 CRM/ERP/SSO/消息队列 / 生产级权限与分布式锁  
- ❌ 模型微调、复杂驾驶舱当成「已上线中台」  
- ❌ 真实客户数据与品牌  
- ❌ 用单 Orchestrator 替代四环  
- ❌ 要求一期把 Rule+LLM / Vision 做成与四环并列的平台环  

---

## 8. 技术选型（摘要）

| 项 | 建议 |
|----|------|
| 语言 | Python 3.11+ |
| LLM | OpenAI 兼容（DeepSeek 等），key 环境变量 |
| 模型 | Pydantic；Skill YAML |
| 入口 | CLI + FastAPI |
| 协作 | run_id + `shared/store` |
| 评测 | Extraction / RAG 金标；Story1/2 冒烟 |

---

## 9. 表述边界

**可写：**

> 虚构企业「青枢出行」下的 Anti-AI-Silo 参考实现：平台统一治理 **4 类控制环 + 3 类工具**，业务以 **Skill** 挂载；共享语义与 AI 产出资产；含 Story1/2 与录屏示意。

**不可写：**

> 已为企业上线 AI 中台 / 多部门生产 Agent 交付。

---

## 10. 完整性检查

- [x] 成品定义为 Loops + Tools + Skills  
- [x] 平台 4 环 + 3 工具类  
- [x] 部门只交 Skill  
- [x] 统一 ToolRegistry + DataFetcher  
- [x] 显式共享资产层  
- [x] 一功能一 Skill；跨功能只经共享层，无 Agent 管道  
- [x] flows 为关系说明，非联跑引擎  
- [x] Story1 / Story2 验收（两次独立运行）  
- [x] 非目标与表述边界  
- [x] 虚构企业：青枢出行  

**裁定：本文为现行总架构；旧「一期 6 类大脑均主清单」叙事废止。**
