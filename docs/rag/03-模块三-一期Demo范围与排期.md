# RAG · 模块三：一期 Demo 范围与排期

> **喂食核心 · RAG 模块三**  
> 对齐 `BLUEPRINT.md` D7（RAG Agent + kb skills）与反孤岛 Story  
> 版本：V1.0 · 2026-08-05

---

## 1. 裁定：一期做什么

### 1.1 必做（P0）

| 项 | 内容 | 验收 |
|----|------|------|
| RAG 控制环 | `agents/rag/`：`retrieve → stuff → generate` | CLI/API：`agent_type=rag` + `skill_id` 可跑 |
| Skill ×3 | `repair_kb` · `policy_kb` · `hr_rules`（YAML + 域白名单） | 三域问答各至少 1 条金标问题答出且带引用 |
| 统一手脚 | 只走 `shared` DataFetcher + `search_kb` / `get_kb_document` | 禁止 `agents/rag/` 私有 fetcher |
| 索引策略 | 一期：**本地 TF-IDF 或简单向量**（蓝图建议）；基于已有 `data/knowledge/**` | 换模型不改 Skill 契约 |
| Catalog | `AGENT_TYPES.rag.status` → 可跑；FEATURES 挂 RAG 功能卡 | 业务墙/运维台可见 |
| 安全 | `kb_domains_allow` 与 ReAct 同闸 | 越域检索被拒 |

### 1.2 一期示意但不深挖（P1）

| 项 | 做法 |
|----|------|
| 渠道流 RAG 节点 | flow 已有；控制环复用 `policy_kb`/`channel` 域，**不**做自动汇合简报 |
| App 问答 F-UO-009 | **复用** `repair_kb`（或 `app_qa` 别名同配置），不新建第二套索引 |
| 可选 `write_ai_output` | 演示「问答也可资产化」；**非** Story1/2 硬依赖 |

### 1.3 明确不做 / 推后（P2+）

| 项 | 原因 |
|----|------|
| 按部门复制向量库 / 多套 embedding 服务 | 反孤岛原则 |
| Multi-Agent：RAG 与 ReAct 自动联跑 | 范围爆炸；一期手工分步 |
| 知识库自动更新管线（F-UO-010） | 属 Extraction→入库工程 |
| 采购/法务/品牌/专利/组织记忆等新域 | 无合成长文或非 Demo 主线 |
| Text2SQL / 指标语义 RAG（F-DAT-002/003） | 问数主轴 ReAct；另开线 |
| 生产级重排、混合检索、GPU、微调 | Demo 级检索足够 |
| 真实客户文档入库 | 合规红线 |

---

## 2. 与 Story1 / Story2 的关系

| Story | RAG 角色 |
|-------|----------|
| Story1 填单资产化 | **不依赖 RAG**；RAG 作为并列「知识大脑」Demo |
| Story2 续费投诉闸门 | **不依赖 RAG**；闸门读共享标签 |
| 反孤岛叙事补强 | 同一 `search_kb` + 同一 knowledge 源被 RAG Skill 与 ReAct 工具共用 → 讲「单手脚」 |

录屏建议：Story1/2 之后加 **30–60s** RAG：维修域一问 + 展示引用 chunk + 提一句「ReAct 也能调同一 search_kb」。

---

## 3. 功能排期（相对其他 Agent）

现状（2026-08-05）：ReAct / Extraction 已有控制环与文档；RAG / Planning / Rule+LLM / Vision 目录多为占位。

| 顺序 | 工作包 | 依赖 | 产出 |
|------|--------|------|------|
| **R0** | 本文档三件套（地图 / 关系 / 范围） | planning + 需求清单 | `docs/rag/*` ✅ |
| **R1** | 文档切片与索引构建 | `data/knowledge` | chunk 表或内存 index；检索 API 冒烟 |
| **R2** | RAG Skill YAML ×3 + schema 扩展 | SCHEMA.md | `skills/repair_kb` 等可加载 |
| **R3** | 控制环 + CLI/API 接通 | R1+R2 · 共享 tools | `status=ready` |
| **R4** | 金标问答集 + 简单评测 | R3 | `docs/rag/eval` 或 scripts |
| **R5** | 业务墙/运维台挂卡 | R3 · catalog | 与 Extraction 同模式 |
| **R6** | flows 补 `service_repair_qa` 等 | R3 | 与 planning 契约一致 |

**并行建议**：R1 可与 Planning/Rule 文档工作并行；R3 不宜与「大改 ToolRegistry」同周冲突。

蓝图工期锚点：原 **D7 ≈ 3h** 为骨架；完整三 Skill + 评测 + UI 建议按 **R1–R5 拆成 2～3 个对话会话**。

---

## 4. 一期 Demo 剧本（建议 3 问）

| # | skill | 用户问（合成） | 期望 |
|---|-------|----------------|------|
| Q1 | `repair_kb` | 续航突然变差怎么排查？ | 命中续航异常文档；步骤+引用 |
| Q2 | `policy_kb` | 2026Q3 提货返利到哪一档？ | 命中返利政策；注明虚构口径 |
| Q3 | `hr_rules` | 坐席质检 SOP 有哪些红线？ | 命中 SOP 要点 |

负面样例：`repair_kb` 问人资制度 → 域闸拒绝或明确「超出本知识域」。

---

## 5. 成功标准（Demo 级）

| 指标 | 门槛 |
|------|------|
| 控制环可跑 | 3 Skill 均能端到端返回 |
| 引用可见 | 终答含 `kb_doc_id` / chunk 或等价引用 |
| 域隔离 | `kb_domains_allow` 越域失败 |
| 无私有 fetcher | code review / 目录检查 |
| 不破坏 Story1/2 | 现有 smoke 仍绿 |

---

## 6. 下一步功能性步骤（实现顺序）

> 本列表即「文档构建 → 索引库 → …」的开工清单；**下一对话从 R1 开始写代码**。

1. **知识文档盘点与切块策略** ✅  
   - 策略：`docs/rag/04-文档切块策略.md`  
   - 产物：`data/knowledge/chunks.json`（`scripts/build_kb_chunks.py`）  
   - 实现：`shared/rag/chunking.py`  

2. **索引库 / 检索器** ✅  
   - 策略：`docs/rag/05-索引库与检索器.md`  
   - 产物：`data/knowledge/tfidf_index.json`（`scripts/build_kb_index.py`）  
   - 实现：`shared/rag/tfidf_index.py`；出口 `DataFetcher.search_kb`  

3. **RAG Skill 契约** ✅  
   - 策略：`docs/rag/06-RAG-Skill契约.md`  
   - 产物：`skills/{repair_kb,policy_kb,hr_rules}/skill.yaml`  
   - 实现：`agents/rag/skill_schema.py` · `skill_loader.py`；分流见 `apps/skill_dispatch.py`  

4. **控制环实现** ✅  
   - 策略：`docs/rag/07-控制环实现与接通.md`  
   - 实现：`agents/rag/agent.py`；CLI / `POST /v1/rag/runs`；冒烟 `scripts/smoke_rag.py`  

5. **金标与冒烟** ✅  
   - 金标：`data/eval/rag/gold_qa.json`（15 条）  
   - 评测：`scripts/eval_rag.py` → `docs/rag/eval_reports/`  
   - 冒烟：`scripts/smoke_rag.py`；说明见 `docs/rag/08-金标评测与冒烟.md`  

6. **Catalog / UI** ✅（RAG Demo 卡 + 业务墙/运维分流已挂）  
   - FEATURES：`F-SVC-002/004` · `F-POL-RAG` · `F-UO-009` · `F-HR-001`  
   - `rag` status=ready；`/v1/rag/runs`  

7. **编排契约回写** ✅  
   - `department_flows.json`：`service_repair_qa` / `user_ops_app_qa` / `order_policy_qa` / `hr_policy_qa`；`channel_ops_board` RAG 节点挂 `policy_kb`  
   - 同步 `docs/planning/02` · catalog `flow_ids`  

8. **（可选）旁路资产化**  
   - RAG 终答 `write_ai_output`，供后续 Planning 消费示意 — **一期未做（有意推迟）**  

---

## 7. 修订

| 版本 | 说明 |
|------|------|
| V1.0 | 一期范围、与 Story 关系、R0–R6 排期与功能性步骤 |
