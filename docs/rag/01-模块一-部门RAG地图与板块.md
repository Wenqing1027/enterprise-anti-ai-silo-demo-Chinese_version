# RAG · 模块一：部门 × RAG 板块地图

> **喂食核心 · RAG 模块一**（对应蓝图 `agents/rag/`）  
> 虚构企业：**青枢出行（Qingshu Mobility）** · 智能电动车出行  
> 控制环：`retrieve → stuff → generate`  
> 原则：**一个 RAG 大脑**；部门/功能差异进 **Skill + kb_domain**，禁止按部门复制索引引擎  
> 版本：V1.0 · 2026-08-05

---

## 0. 口径

| 概念 | 含义 |
|------|------|
| **RAG Agent** | 独立控制环：检索 → 装填上下文 → 生成；运维台 `agent_type=rag` |
| **Skill** | 挂载域、提示槽、成功标准（如 `repair_kb` / `policy_kb` / `hr_rules`） |
| **kb_domain** | 知识分区：已有 `repair` · `policy` · `hr` · `product` · `channel`（见 `data/knowledge/`） |
| **ReAct + search_kb** | 工具调用路径也可查知识库——**不是** RAG Agent 本体；与 RAG 正交、可并行 |

本文件列出：**所有部门**中「建议走 RAG 板块」的功能，并标注一期 Demo 与规格占位。  
关系编排见 [02](./02-模块二-与其他Agent关系编排.md)；一期切分见 [03](./03-模块三-一期Demo范围与排期.md)。

---

## 1. 知识域 ↔ Skill 对照（底座）

| kb_domain | 已有文档（示意） | 建议 Skill | 主责消费部门 |
|-----------|------------------|------------|--------------|
| `repair` | 续航/电机/绑车/刹车/充电 | `repair_kb` ★ | 服务 · 用户运营/App · IoT |
| `policy` | 三包电池 · 提货返利 · 续费红线 · 门店 VI | `policy_kb` ★ | 订单/政策 · 渠道 · 战区 · 用户运营 |
| `hr` | 员工制度 · 坐席 SOP | `hr_rules` ★ | 人资 ·（坐席质检旁路） |
| `product` | 车型卖点 · OTA 说明 | `product_kb` | 新零售 · 产品运营 · App |
| `channel` | 提货话术 · 开店清单 | `channel_kb` | 渠道处 · 战区 |

★ = 蓝图一期明确挂载 Skill；`product_kb` / `channel_kb` 可复用同一 RAG 控制环，Skill YAML 分期补齐。

跨部门底座能力：`F-X-001` 数字资产库、`F-DAT-010/011/012` —— **供给层**，不单独再造第二个检索引擎。

---

## 2. Catalog 部门 × RAG 板块

对齐 `apps/catalog.DEPARTMENTS`。表格列：

- **RAG 板块**：本部门内应以 RAG 主控（或强依赖知识问答）的业务块  
- **功能ID**：来自 `docs/AI功能需求清单.md`  
- **Demo**：✅ 一期必做 · 📋 规格占位 · — 本部门无独立 RAG 主控（仅消费共享/旁路）

### 2.1 服务事业部 `service`

| RAG 板块 | 功能ID | Skill / 域 | Demo | 说明 |
|----------|--------|------------|------|------|
| 智能辅助回答 | F-SVC-002 | `repair_kb` · repair | ✅ | 坐席侧话术/知识推荐主路径 |
| 维修知识库问答 | F-SVC-004 · F-DAT-011 | `repair_kb` | ✅ | 与 F-SVC-002 同 Skill，入口话术不同 |
| 维修客服专席 | F-SVC-003 | repair + ReAct 查车/工单 | 📋→旁路 | **问答主轴 RAG**；多步查主数据走 ReAct（可并行准备） |

### 2.2 用户运营 / App `user_ops`

| RAG 板块 | 功能ID | Skill / 域 | Demo | 说明 |
|----------|--------|------------|------|------|
| App 智能问答 MVP | F-UO-009 | `repair_kb`（+ 少量 product） | ✅ | 降 400；与服务共域，Skill 可同或加 `app_qa` 别名 |
| 知识库自动更新 | F-UO-010 | Extraction → 写 kb | 📋 | RAG **消费**更新后的库；更新管线非 RAG 控制环 |
| AIGC 文案/Push | F-UO-013 | product/policy 检索增强 | 📋 | 检索作素材，生成主轴可挂 Planning |
| 统一智能客服 | F-UO-019 | repair + ReAct | 📋 | 二期；问答段复用 `repair_kb` |

### 2.3 运营管理 · 订单/政策 `order_policy`

| RAG 板块 | 功能ID | Skill / 域 | Demo | 说明 |
|----------|--------|------------|------|------|
| 政策口径问答 | F-OPS-004 旁路 | `policy_kb` · policy | ✅ | 解析主轴是 Extraction+Rule；**纯问答**走 RAG |
| 加盟风控知识辅助 | F-OPS-006 | policy + risks 文本 | 📋 | 规则闸门主轴；RAG 作条款检索 |

### 2.4 四大战区 `warzone`

| RAG 板块 | 功能ID | Skill / 域 | Demo | 说明 |
|----------|--------|------------|------|------|
| 线下问答 RAG | F-WZ-001 | policy/channel/product | 📋 | 经销商/门店问答；一期可展示卡片，跑通复用 `policy_kb` |
| 提货方案话术 | F-WZ-001 子项 | channel | 📋 | 与渠道 `channel_kb` 同域 |

### 2.5 渠道处 `channel`

| RAG 板块 | 功能ID | Skill / 域 | Demo | 说明 |
|----------|--------|------------|------|------|
| 渠道/政策知识问答 | F-OPS-001 知识段 | `channel_kb` / `policy_kb` | ✅ 示意 | 与 `channel_ops` ReAct **并行**（见 flow `channel_ops_board`） |
| 开店推进知识 | F-OPS-013 旁路 | channel | 📋 | Planning 出包；RAG 答「怎么开店检查」 |

### 2.6 新零售 `retail`

| RAG 板块 | 功能ID | Skill / 域 | Demo | 说明 |
|----------|--------|------------|------|------|
| 多平台客服知识答 | F-RET-001/002 | product（+repair） | 📋 | ReAct 查单/库存；知识段 RAG 并行 |

### 2.7 采购平台 `procurement`

| RAG 板块 | 功能ID | Skill / 域 | Demo | 说明 |
|----------|--------|------------|------|------|
| 合作风控条款检索 | F-PUR-002 | 专用域（暂无） | 📋 | 一期不建采购 kb；卡片展示 |

### 2.8 数据研究院 / 数字资产 `data_lab` · `shared`

| RAG 板块 | 功能ID | Skill / 域 | Demo | 说明 |
|----------|--------|------------|------|------|
| 内部知识库底座 | F-DAT-010 · F-X-001 | 全域 index | ✅ 底座 | **索引/切块/域路由**归共享层，非业务 Skill |
| 指标语义层问答 | F-DAT-002 | 语义字典 | 📋 | 问数主轴 ReAct/Text2SQL；RAG 辅助释义 |
| 资产结构化入库 | F-DAT-012 | Extraction → kb | 📋 | 供给管线 |

### 2.9 人资管理平台 `hr`

| RAG 板块 | 功能ID | Skill / 域 | Demo | 说明 |
|----------|--------|------------|------|------|
| 制度问答 / 员工助理 | F-HR-001 · F-HR-003 | `hr_rules` · hr | ✅ | 蓝图一期 Skill；跨部门只读同库 |
| 招聘客服知识 | F-HR-002 | hr | 📋 | 匹配段 Extraction；问答段 RAG |

### 2.10 IoT / 车机 `iot`

| RAG 板块 | 功能ID | Skill / 域 | Demo | 说明 |
|----------|--------|------------|------|------|
| OTA/故障知识旁路 | F-IOT-002 旁路 | product/repair | 📋 | 主轴 Rule+LLM；RAG 解释版本文档 |

### 2.11 用研 / VoC `voc`

| RAG 板块 | 功能ID | Skill / 域 | Demo | 说明 |
|----------|--------|------------|------|------|
| VoC Agent 场景向导 | F-VOC-022 | 方法论/手册 kb | 📋 | Planning+RAG；一期不建 VoC 手册库 |

---

## 3. Catalog 外部门（需求全量，Demo 仅展示/占位）

| 部门（需求清单） | RAG 板块代表 | 功能ID | Demo |
|------------------|--------------|--------|------|
| 战略 / 管理层 | 智能问数释义、社媒/竞品季报 | F-STR-001/005 | 📋 |
| 品牌运营 / 研究院 | GEO、MI 文本、社会形象、素材口径 | F-BRD-007/008/014 等 | 📋 |
| 产品运营 / 技术研究院 | 竞品情报、研发洞察、电机电池图谱 | F-PRD-001/002/004/005 | 📋 |
| 法务监察 | 合同条款检索 | F-LEG-001 | 📋 |
| 秘书办 | 新闻稿素材检索增强 | F-SEC-001 | 📋 |
| IT / 流程 | 组织记忆向量库 | F-IT-005 | 📋 |
| 制造 / 品质 | （主轴 Vision；无独立一期 RAG） | — | — |
| 供应 / 财经 / 零售质检 | 偶发条款检索，不单建 Skill | — | — |

---

## 4. 总览：一期必跑 RAG 资产

| 优先级 | skill_id | kb_domains_allow | 对齐功能 | 状态（现状） |
|--------|----------|------------------|----------|--------------|
| P0 | `repair_kb` | `repair` | F-SVC-002/004 · F-UO-009 · F-DAT-011 | 目录占位，控制环未建 |
| P0 | `policy_kb` | `policy` | 政策问答 · 渠道并行段 · F-OPS 旁路 | 目录占位 |
| P0 | `hr_rules` | `hr` | F-HR-001/003 | 待建目录+YAML |
| P1 | `channel_kb` 或复用 policy | `channel` | `channel_ops_board` RAG 节点 | planned |
| P2 | `product_kb` | `product` | 新零售/App 卖点答 | planned |

机读能力目录已有 `repair_kb` / `policy_kb` 条目（`capability_catalog.json`）；**缺**控制环与 `skill.yaml`。

---

## 5. 与其他文档

| 文档 | 关系 |
|------|------|
| [02 · 关系编排](./02-模块二-与其他Agent关系编排.md) | 并行/串行/正交 |
| [03 · 一期范围](./03-模块三-一期Demo范围与排期.md) | 做/不做/排期 |
| [docs/planning/02](../planning/02-模块二-分部门编排图.md) | 渠道流已含 RAG 并行节点 |
| [docs/react/02](../react/02-模块二-分部门工具箱.md) | ReAct 侧 `search_kb` 白名单 |
| [BLUEPRINT.md](../../BLUEPRINT.md) | L2 RAG · L3 Skill · D7 工期 |
