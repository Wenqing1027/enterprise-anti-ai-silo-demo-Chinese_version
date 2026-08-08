# Agent 编排：并行 vs 串行（接入网页前必读）

> 青枢出行 Demo · 业务墙 `/business` + 运维台 `/ops`  
> **总架构 V2**：[BLUEPRINT.md](../BLUEPRINT.md)（平台 4 环 × 3 类工具 + Skills）  
> 机读契约：`data/entities/department_flows.json`  
> 版本：V1.2 · 2026-08-06

---

## 1. 一句话

| 模式 | 含义 | Demo 怎么表现 |
|------|------|----------------|
| **单功能运行** | 一次只跑一个 Skill（一功能） | 点一张功能卡 → 一次 API run |
| **并行（关系）** | 两功能无强制数据依赖，可分别试跑 | 卡片并排；均可「打开运行」 |
| **串行（关系）** | 下游功能通常需上游已写入共享层；仍是 **两次独立运行** | 标「依赖共享产出」；**不**自动联跑；**不** Agent 对话交接 |

反孤岛原则：跨功能只经 `AIOutput` / 共享标签；**一功能一 Skill**；不做 Multi-Agent 互聊或管道接力。

---

## 2. 优先判定表（接入网页用）

### 2.1 并行（可并排试跑 / 并排展示）

| 组 | 成员 | 关系说明 |
|----|------|----------|
| Story1 填单双脑 | Extraction `ticket_fields` ∥ ReAct `fill_ticket` | 同目标可选路径，不必先抽后填 |
| VoC 双 Skill | `voc_entities` ∥ `voc_tagging` | 同 Schema 别名，运维等价试跑 |
| 维修 RAG ⊥ Story1 | RAG `repair_kb` ⊥ 填单双脑 | **正交并行**：问答不写工单主路径，填单不依赖 RAG |
| App RAG ⊥ 续费闸门 | RAG `F-UO-009` ⊥ Story2 闸门 | 续费不读 RAG 答案 |
| 政策 RAG ⊥ 审单串行 | RAG `policy_kb` ⊥ `order_policy_review` | 口径问答不替代 Rule 档位闸门 |
| 渠道看板准备 | ReAct `channel_ops` ∥ RAG `policy_kb` | 可并行取数/取口径；**汇合 Planning 仍 planned** |
| 质检准备 | Vision ∥ Extraction | 并行取证后串行汇合（示意） |
| 人资 RAG | `hr_rules` 单节点 | standalone；跨部门只读同域 |

### 2.2 串行（必须先上游，再下游说明）

| 链路 | 顺序 | 网页表现 |
|------|------|----------|
| Story2 续费闸门 | 上游 Extraction/ReAct 写出阻断 tag → 共享层 → 下游续费触达 | `F-UO-017` 等标「串行下游」；分步说明，不联跑 |
| 审单 | Extraction 抽单 → Rule+LLM 闸门 → ReAct 查数 | 订单部门「展示」+ 串行说明 |
| 渠道看板汇合 | （并行准备完成后）→ Planning 汇合 | 汇合节点 planned |
| 质检汇合 | Vision∥Extraction → Rule 告警 | IoT 展示 |

**RAG 自身控制环是线性的**（retrieve → stuff → generate → cite），但相对其它 Agent **不构成跨脑串行依赖**（除渠道看板「汇合」示意外）。

### 2.3 RAG 机读流（`department_flows.json`）

| flow_id | Skill | 与其它脑 |
|---------|-------|----------|
| `service_repair_qa` | `repair_kb` | ∥ Story1 |
| `user_ops_app_qa` | `repair_kb` | ∥ 续费闸门 |
| `order_policy_qa` | `policy_kb` | ∥ 审单串行示意 |
| `hr_policy_qa` | `hr_rules` | standalone |
| `channel_ops_board` | `channel_ops` ∥ `policy_kb` → Planning | 准备并行；汇合 planned |

---

## 3. 一期真实可跑链路（摘要）

### 3.1 并行（同故事、不同大脑）

```text
同一业务目标「工单草案资产化 / Story1」：

  [Extraction · ticket_fields]  ──┐
                                  ├──► write_ai_output ──► 共享层
  [ReAct · fill_ticket]         ──┘

另： [RAG · repair_kb]  ──► 带引用终答（与上图正交并行，不进写共享主路径）
```

### 3.2 串行（必须先有上游标签）

```text
Story2 续费闸门：

  上游（服务/VoC Extraction 或 ReAct 填单）
        │  write_ai_output（含阻断 tag）
        ▼
  共享层 Tag / AIOutput
        │  read_shared_tags / check_outreach_block
        ▼
  下游 Planning/Rule（续费触达）—— 一期契约已有，控制环可仍为 planned
```

网页说明口径：

1. 先在服务/用研跑 **Demo 可跑** 的 Extraction 或 ReAct 填单，写出投诉/风险标签。  
2. 再到用户运营看「投诉闸门」卡片（可展示 + 说明串行依赖）；完整 `renewal_plan` 跑通属 Planning 线。

---

## 4. 网页接入规则（本步实现）

| 页面 | Demo 可跑（`demo_ready`） | 非 Demo |
|------|---------------------------|---------|
| **业务墙 `/business`** | 一卡一 Skill 真调对应 API；展示共享依赖说明 | planned 卡只展示 |
| **运维台 `/ops`** | **故障排查**：日志流 / 指标 / 链路 / 共享产出 | **不**做 Skill 试跑或规章问答 |

API 映射：

| Agent | Endpoint |
|-------|----------|
| ReAct | `POST /v1/react/runs` |
| Extraction | `POST /v1/extraction/runs` |
| RAG | `POST /v1/rag/runs` |

不做：一键自动串跑多个 Agent（避免一期范围爆炸）。

---

## 5. 修订

| 版本 | 说明 |
|------|------|
| V1.2 | 运维台纠偏为故障排查（非 Skill 试跑墙） |
| V1.1 | RAG 判定表；双页可跑含 RAG；渠道并行准备说明 |
