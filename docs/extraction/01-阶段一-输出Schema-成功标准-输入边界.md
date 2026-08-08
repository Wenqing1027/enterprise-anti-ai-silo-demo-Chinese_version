# Extraction Agent · 阶段一：输出 Schema · 成功标准 · 输入边界

> **喂食核心 · Extraction 阶段一**（对应蓝图 `agents/extraction/`）  
> 虚构企业：**青枢出行（Qingshu Mobility）** · 智能电动车出行  
> 控制环：`schema → extract → validate`  
> 字段对齐：`docs/标准字段定义表.md`、`shared/models`  
> 版本：V1.0 · 2026-08-05  
> **口径**：本阶段对 **所有涉及 Extraction 的部门/功能** 均给出「提取什么 / 成功标准 / 输入边界」——**不论是否进 Demo 实现**。Demo 必做仅标注 ✅。

---

## 0. 范围与约定

### 0.1 阶段一覆盖

| 类别 | 说明 |
|------|------|
| ✅ **Demo 必做** | `ticket_fields`（对齐 F-SVC-001）、`voc_entities` / `voc_tagging`（对齐 F-VOC-002 及服务 VoC 回流） |
| 📋 **规格占位** | 需求清单中其余 Extraction（含组合型）功能：本文件定义 Schema/标准/边界，**不实现控制环** |

### 0.2 成功标准口径（统一）

| 指标 | 含义 | 评测方式（Demo） |
|------|------|------------------|
| **Schema 合规率** | 输出通过 JSON Schema / Pydantic 校验 | 自动化断言 |
| **必填字段召回** | 金标中「应有」的必填字段被抽出 | 字段级 recall |
| **枚举准确率** | 枚举字段与金标一致 | exact match |
| **容忍度** | 允许空值 / 低置信度 / 人工确认的边界 | 见各功能卡 |
| **阻断类零漏报** | 影响 Story2 的投诉/风险标签不得漏 | 专项金标集 |

**Demo 级默认门槛**（规则抽取或轻量 LLM）：Schema 合规 **100%**；核心枚举准确 **≥75%**；阻断类标签漏报 **=0**。  
**规格占位功能** 给出目标门槛，供后续落地，不作为本期验收。

### 0.3 输入边界总则

| 允许（阶段一） | 禁止 |
|----------------|------|
| UTF-8 纯文本、通话/客服转写文本、合成 JSON 种子 | 真实客户 PII 明文、真实品牌名 |
| 已转写的 `.txt` / `.md`、结构化 `.json` 载荷 | 未转写原始音频/视频作为 Extraction 主输入（转写属前置） |
| 截断后 ≤4k 字符的单条原声（过长先切片） | 把 RAG 长文问答、Vision 像素级任务塞进本脑 |

机器可读 Schema 文件：`docs/extraction/schemas/`。

### 0.4 总览索引

| 功能ID | 部门 | 功能名 | Demo | Skill / Schema ID |
|--------|------|--------|------|-------------------|
| F-SVC-001 | 服务事业部 | 智能填单 | ✅ | `ticket_fields` / `ticket_draft_v1` |
| F-VOC-002 | 用研/运营 | 自动打标+情感 | ✅ | `voc_entities` / `voc_entities_v1` |
| F-SVC-006 | 服务事业部 | NLP 聚类+语料回流 | ✅ 同源 | 复用 `voc_entities_v1` + 批量 |
| F-SVC-009 | 服务/品牌 | VoC 系统（单条抽） | ✅ 同源 | 复用 `voc_entities_v1` |
| F-X-003 | 跨部门 | VoC 标签库回流 | ✅ 消费链 | 产出进 `TagVocabulary` / `AIOutput` |
| F-SVC-005 | 服务事业部 | VOC 故障聚类 | 📋 | `voc_cluster_v1` |
| F-SVC-007 | 服务事业部 | 问题类型预测 | 📋 | `issue_predict_v1` |
| F-SVC-008 | 服务/品牌 | 智能质检 | 📋 | `sop_qc_v1` |
| F-VOC-001 | 售后/客服 | 多渠道汇聚+转写 | 📋 | `voc_ingest_v1`（半结构化） |
| F-VOC-023 | 用研/运营 | 标签体系订正 | 📋 | `tag_revise_v1` |
| F-VOC-025 | 用研 | 开放题打标 | 📋 | 复用 `voc_entities_v1` |
| F-VOC-015 | 品牌/公关 | 公开舆情弱监测 | 📋 | `pr_hotspot_v1` |
| F-VOC-017 | 区域/门店 | 情绪地图切片 | 📋 | `emotion_slice_v1` |
| F-DAT-006 | 数据研究院 | 矩阵账号监测宽表 | 📋 | `matrix_account_v1` |
| F-DAT-012 | 数字资产底座 | 资产结构化入库 | 📋 | `asset_struct_v1` |
| F-DAT-013 | 底座/服务 | 智能客服底座 NLP | 📋 | 复用填单+打标 Schema |
| F-STR-005 | 战略/品牌 | 社媒情感+竞品季报 | 📋 | `brand_signal_v1` |
| F-BRD-005 | 品牌/零售 | 矩阵监测 | 📋 | 复用 `matrix_account_v1` |
| F-BRD-008 | 品牌研究院 | MI NLP 语义 | 📋 | `mi_semantic_v1` |
| F-BRD-009 | 品牌/公关 | 全媒体舆情 | 📋 | `pr_monitor_v1` |
| F-BRD-013 | 品牌研究院 | BVP 首测 | 📋 | `bvp_test_v1` |
| F-BRD-014 | 品牌研究院 | 社会形象诊断 | 📋 | `image_diag_v1` |
| F-BRD-015 | 品牌/数字化 | App 体验审计 | 📋 | `ux_audit_v1` |
| F-BRD-017 | 品牌研究院 | NPS 实时采集 NLP | 📋 | 复用 `voc_entities_v1` |
| F-OPS-004 | 订单/政策 | 销售政策解析 | 📋 | `policy_parse_v1` |
| F-OPS-011 | 渠道/零售 | 标杆复制路径 | 📋 | `benchmark_actions_v1` |
| F-WZ-004 | 战区/零售 | 导购人效诊断 | 📋 | `guide_efficacy_v1` |
| F-MFG-002 | 制造/品质 | PDA 车架件绑定 | 📋 | `pda_bind_v1` |
| F-MFG-006 | 品质 | 追溯数据包 | 📋 | `trace_package_v1` |
| F-PRD-001 | 产品运营 | 竞品信息收集 | 📋 | `competitor_card_v1` |
| F-PRD-004 | 产品创新院 | 专利/技术成熟度 | 📋 | `patent_cluster_v1` |
| F-FIN-001 | 财经 | 三单匹配抽取 | 📋 | `tri_doc_match_v1` |
| F-HR-002 | 人资 | 岗位匹配抽取 | 📋 | `job_match_v1` |
| F-LEG-001 | 法务监察 | 合同风险点抽取 | 📋 | `contract_risk_v1` |
| F-UO-006 | 用户运营 | 外呼意向标记 | 📋 | `renew_intent_v1` |
| F-UO-010 | 用户运营 | 高频问题摘要入库 | 📋 | `faq_digest_v1` |
| F-UO-011 | 用户运营 | 分群特征抽取 | 📋 | `segment_feat_v1` |
| F-UO-015 | 用户运营 | KOC 识别 | 📋 | `koc_candidate_v1` |
| F-UO-016 | 用户运营 | UGC 文本审核 | 📋 | `ugc_moderation_v1` |
| F-IT-001 | IT/流程 | AI 冗余检测 | 📋 | `process_dup_v1` |

---

## 1. Demo 必做功能卡

### 1.1 F-SVC-001 · 智能填单 · `ticket_fields` ✅

| 项 | 内容 |
|----|------|
| **部门** | 服务事业部 |
| **提取什么** | 非结构化客服对话/描述 → **工单草案** `ticket_draft_v1` |
| **Skill** | `ticket_fields`（ReAct 侧复用 tool `extract_ticket_fields`） |
| **落库** | `AIOutput.payload`，`payload_schema=ticket_draft_v1`；`consumer_allow` 含 `renewal_plan`、`voc_tagging` |
| **机器 Schema** | [`schemas/ticket_draft_v1.json`](./schemas/ticket_draft_v1.json) |

#### 输出 Schema（`ticket_draft_v1`）

| 字段 | 类型 | 必填 | 枚举/约束 | 标准字段 |
|------|------|------|-----------|----------|
| `customer_id` | string\|null | 条件必填* | `CUS-\d+` | SF-0037 |
| `vin` | string\|null | 条件必填* | `QS0` + 14 位合成 | SF-0068 |
| `ticket_type` | enum | ✅ | `fault\|consult\|complaint\|other` | SF-0224 |
| `fault_category` | enum\|null | fault 时建议 | `battery\|motor\|brake\|controller\|charging\|dashboard\|frame\|lighting\|tire\|other` | SF-0225 |
| `consult_category` | string\|null | consult 时建议 | 自由短标签 | SF-0226 |
| `ticket_channel` | string | ✅ | `400\|App\|电商\|门店\|community` | SF-0227 |
| `ticket_status` | enum | ✅ | 草案默认 `open` | SF-0228 |
| `tag_id` | string | ✅ | 必须 ∈ `TagVocabulary` | SF-0245 |
| `sentiment` | enum | ✅ | `pos\|neu\|neg` | SF-0248 |
| `desc_text` | string | ✅ | 1–1000 字，脱敏后原文摘要 | SF-0233 |
| `is_complaint` | boolean | ✅ | 投诉或阻断标签为 true | SF-0231 |
| `confidence` | number | 建议 | 0–1；规则抽取可固定 0.6 | — |
| `needs_human_review` | boolean | 建议 | 低置信或缺 ID 时 true | — |

\* 文本能抽则抽；抽不到允许 `null`，但须 `needs_human_review=true`。

#### 成功标准

| 指标 | 门槛 | 容忍度 |
|------|------|--------|
| Schema 合规率 | **100%** | 不合规 → 整单失败，禁止写 `AIOutput` |
| `ticket_type` 准确率 | ≥ **80%**（Demo 金标 ≥20 条） | 边界句（故障兼投诉）允许标 `complaint` |
| `fault_category` 准确率 | ≥ **75%**（仅 fault 子集） | 未知 → `other`，**不算错** |
| `tag_id` Top-1 命中 | ≥ **75%**；阻断标签漏报 **0** | 多标签场景只评主标签 |
| `sentiment` 准确率 | ≥ **80%** | `neu`/`neg` 混淆在非投诉句可容忍 1 档 |
| ID 抽取（有明示时） | VIN/CUS 召回 **≥95%** | 未明示允许 null |
| 时延（单条） | Demo ≤ 3s（规则）/ ≤ 8s（LLM） | — |

#### 输入边界

| 支持 | 不支持 |
|------|--------|
| 客服对话纯文本、400 转写 `.txt`、App 反馈文本、种子 JSON 的 `text` 字段 | 原始 `.wav/.mp3`（须先转写） |
| 单条 ≤4000 字符；中英混排 | PDF/图片工单扫描件（归 Vision/OCR） |
| 渠道元数据可选：`channel`、`customer_id`、`vin` 作为提示而非必须 | 多会话合并成一篇超长纪要（须先切片） |

---

### 1.2 F-VOC-002 · 自动打标 + 情感 · `voc_entities` ✅

| 项 | 内容 |
|----|------|
| **部门** | 用研 / 运营（服务侧同源消费） |
| **提取什么** | 原声文本 → **VoC 实体包**（标签、情感、主题、风险） |
| **Skill** | `voc_entities` / 能力目录 `voc_tagging` |
| **落库** | `AIOutput`（`payload_schema=voc_entities_v1`）+ 对齐共享 `TagVocabulary` 引用 |
| **机器 Schema** | [`schemas/voc_entities_v1.json`](./schemas/voc_entities_v1.json) |
| **同源复用** | F-SVC-006 / F-SVC-009（单条）/ F-VOC-025 / F-BRD-017（单条 NLP）/ F-X-003 |

#### 输出 Schema（`voc_entities_v1`）

| 字段 | 类型 | 必填 | 枚举/约束 | 标准字段 |
|------|------|------|-----------|----------|
| `feedback_id` | string\|null | 建议 | 无则运行时生成 `FB-*` | SF-0240 |
| `sample_voice` | string | ✅ | 脱敏原声，≤500 字 | SF-0258 |
| `tag_id` | string | ✅ | ∈ TagVocabulary | SF-0245 |
| `tag_name` | string | ✅ | 与字典一致 | SF-0246 |
| `tag_domain` | enum | ✅ | `product\|service\|app\|channel\|risk` | SF-0247 |
| `sentiment` | enum | ✅ | `pos\|neu\|neg` | SF-0248 |
| `sentiment_score` | number | 建议 | [-1, 1] | SF-0249 |
| `problem_theme` | string | ✅ | 主题短名 | SF-0250 |
| `severity_risk_level` | enum\|null | 条件 | 舆情/安全相关时 `P0\|P1\|P2` | SF-0260 |
| `clue_confidence` | enum | ✅ | `weak\|medium`（Demo 无 strong） | SF-0259 |
| `customer_id` | string\|null | 可选 | `CUS-*` | SF-0037 |
| `vin` | string\|null | 可选 | `QS0*` | SF-0068 |
| `secondary_tag_ids` | string[] | 可选 | ≤3，均须在字典内 | — |
| `needs_human_review` | boolean | ✅ | 字典未命中或 weak 时 true | — |

#### 成功标准

| 指标 | 门槛 | 容忍度 |
|------|------|--------|
| Schema 合规率 | **100%** | 同填单 |
| `tag_id` 命中（主标签） | ≥ **80%** | 近义标签若同 `tag_parent_id` 可记「可接受」 |
| **阻断标签漏报**（`TAG-投诉未结` / `TAG-舆情风险` / `TAG-安全隐患` / `TAG-三包争议`） | **0** | 多标时主标签或 secondary 任一命中即可 |
| `sentiment` 准确率 | ≥ **85%**（硬条件，与看板同期） | 仅允许 `pos`↔`neu` 在非风险句混淆 |
| `tag_domain` 准确率 | ≥ **90%** | — |
| 字典外标签率 | **≤5%** | 字典外必须 `needs_human_review=true` 且不得直接进共享阻断逻辑 |
| 批量（F-SVC-006） | 条级达标且失败条可隔离 | 单条失败不阻断整批写库 |

#### 输入边界

| 支持 | 不支持 |
|------|--------|
| 400/社区/满意度开放题纯文本、转写文本、工单 `desc_text` | 原始录音、图片表情包 OCR 主路径 |
| 单条原声；批量 JSONL（每行一条 `text`） | 未建字典时的「自由造标签」写共享层 |
| 渠道字段可选：`source_channel` | 把聚合格报表字段（NPS 周环比等）当作单条抽取目标 |

---

### 1.3 Demo 同源说明（不另建控制环）

| 功能ID | 与 Demo 关系 | 额外约束 |
|--------|--------------|----------|
| **F-SVC-006** | 批量调用 `voc_entities_v1` | 输出可附 `cluster_hint`（可选字符串），聚类算法本身非 Extraction 必做 |
| **F-SVC-009** | 单条同 Schema；报表聚合归 Planning | Extraction 只保证条级结构化 |
| **F-X-003** | 消费 `tag_id` 写入/更新标签库引用 | 不改 Schema；校验 `tag_vocab_version` 一致 |

---

## 2. 规格占位功能卡（阶段一只定契约）

> 下列功能 **本期不实现 Extraction 控制环**，但部门/功能契约在阶段一锁死，避免后期字段漂移。

### 2.1 服务事业部

#### F-SVC-005 · VOC 故障聚类 · `voc_cluster_v1`

| 维度 | 定义 |
|------|------|
| **提取什么** | 多条已打标 VoC → 聚类主题：`theme_id`, `problem_theme`, `member_feedback_ids[]`, `theme_cnt`, `neg_ratio`, `top_tag_ids[]` |
| **成功标准** | Schema 100%；主题纯度（同主题主 tag_domain 一致）≥70%；空簇率 ≤5% |
| **容忍度** | 小样本（&lt;5 条）允许 `clue_confidence=weak` |
| **输入边界** | 仅接受已符合 `voc_entities_v1` 的 JSON 数组；拒绝原始长文 |

#### F-SVC-007 · 客服问题预测 · `issue_predict_v1`

| 维度 | 定义 |
|------|------|
| **提取什么** | 短文本 → `pred_ticket_type`, `pred_fault_category`, `pred_tag_id`, `confidence` |
| **成功标准** | Top-1 类型准确 ≥75%；confidence 校准误差 Demo 不考核 |
| **容忍度** | `confidence&lt;0.4` 可输出 `other` + 人工审 |
| **输入边界** | ≤500 字关键词/首句；非完整通话录音 |

#### F-SVC-008 · 智能质检 · `sop_qc_v1`

| 维度 | 定义 |
|------|------|
| **提取什么** | 转写文本 → `sop_item[]` × `{sop_item, sop_pass_fail, evidence_span}`, `risk_words[]`, `overall_pass` |
| **成功标准** | 必检 SOP 项召回 ≥90%；`risk_words` 精确率 ≥70%（容忍同义） |
| **容忍度** | 证据 span 偏移 ±20 字可接受 |
| **输入边界** | 坐席通话转写 `.txt`；需可选 `agent_id`；不支持纯音频 |

---

### 2.2 VoC / 用研 / 区域

#### F-VOC-001 · 多渠道汇聚+转写 · `voc_ingest_v1`

| 维度 | 定义 |
|------|------|
| **提取什么** | 渠道信封 → `source_channel`, `raw_uri`, `transcript_text`, `lang`, `ingested_at`（转写质量元数据，非整句 NLP） |
| **成功标准** | 信封字段齐全率 100%；转写文本非空 |
| **容忍度** | 转写 WER Demo 不考核；空音频标记 `failed` |
| **输入边界** | 元数据 JSON + 已转写文本；ASR 本身可外包，不进 Extraction 脑 |

#### F-VOC-023 · 标签体系订正 · `tag_revise_v1`

| 维度 | 定义 |
|------|------|
| **提取什么** | 人工/模型建议 → `tag_id`, `action(add\|merge\|deprecate\|rename)`, `tag_name`, `tag_domain`, `tag_parent_id`, `tag_vocab_version` |
| **成功标准** | 动作合法性 100%；无环；域名枚举合法 |
| **容忍度** | rename 允许暂留别名表 |
| **输入边界** | 结构化修订单 JSON；禁止从散文直接改生产字典 |

#### F-VOC-025 · 开放题 AI 打标

复用 **`voc_entities_v1`**。输入限满意度问卷开放题文本；`module_name` 可附加为扩展字段。

#### F-VOC-015 · 公开舆情弱监测 · `pr_hotspot_v1`

| 维度 | 定义 |
|------|------|
| **提取什么** | 公开文本片段 → `topic`, `sentiment`, `severity_risk_level`, `source_url`(可假), `sample_voice` |
| **成功标准** | 风险等级漏报（应 P0/P1）=0；主题非空 |
| **容忍度** | URL 可合成；不追求全网召回 |
| **输入边界** | 免费公域文本快照 `.txt/.json`；不接付费社媒 API |

#### F-VOC-017 · 情绪地图切片 · `emotion_slice_v1`

| 维度 | 定义 |
|------|------|
| **提取什么** | 已打标集合 + 维度键 → `dim_key(region\|store\|channel)`, `dim_value`, `neg_ratio`, `feedback_cnt`, `top_themes[]` |
| **成功标准** | 聚合键合法；计数与成员一致 |
| **容忍度** | 稀疏维（&lt;10 条）标注 `weak` |
| **输入边界** | 仅结构化 VoC 记录；非自由文本 |

---

### 2.3 数据 / 数字资产 / 战略品牌

#### F-DAT-006 / F-BRD-005 · 矩阵账号监测 · `matrix_account_v1`

| 维度 | 定义 |
|------|------|
| **提取什么** | 账号周报半结构化文本/表 → `channel_account_id`, `platform`, `post_cnt`, `play_cnt`, `interact_cnt`, `period` |
| **成功标准** | 账号 ID 与主数据可对齐率 ≥90%；数值解析准确 ≥95% |
| **容忍度** | 缺指标填 null + `needs_human_review` |
| **输入边界** | CSV/JSON 宽表、Markdown 表；不支持纯短视频文件 |

#### F-DAT-012 · 数字资产结构化 · `asset_struct_v1`

| 维度 | 定义 |
|------|------|
| **提取什么** | 文档元数据 → `asset_id`, `title`, `doc_type`, `kb_domain`, `keywords[]`, `summary≤200字` |
| **成功标准** | 元数据必填 100%；`kb_domain` ∈ 允许域 |
| **容忍度** | summary 允许抽失败留空 |
| **输入边界** | PDF/Word **已抽取文本**、MD；视频仅取字幕文本；不做版面还原 |

#### F-DAT-013 · 智能客服底座

填单段复用 `ticket_draft_v1`；NLP 打标段复用 `voc_entities_v1`。无独立 Schema。

#### F-STR-005 · 品牌战略信号 · `brand_signal_v1`

| 维度 | 定义 |
|------|------|
| **提取什么** | 舆情摘要+竞品段落 → `signal_type(sentiment\|competitor)`, `claim`, `sentiment`, `period`, `severity_risk_level?` |
| **成功标准** | claim 非空；类型枚举合法 |
| **容忍度** | 竞品名用虚构代号 |
| **输入边界** | 季报/舆情摘要文本；非原始爬虫 HTML 全集 |

#### F-BRD-008 · MI 语义 · `mi_semantic_v1`

| 维度 | 定义 |
|------|------|
| **提取什么** | 官网/演讲/客服话术对比 → `statement`, `channel`, `consistency_score_0_1`, `conflict_flag`, `evidence_spans[]` |
| **成功标准** | conflict 漏报（明显矛盾）≤10% |
| **容忍度** | score ±0.15 |
| **输入边界** | 成对文本 JSON；单侧文本拒跑 |

#### F-BRD-009 · 全媒体舆情 · `pr_monitor_v1`

扩展 `pr_hotspot_v1`：增加 `media_tier`, `volume_proxy`, `alert_flag`。输入为监测快照 JSONL。

#### F-BRD-013 · BVP 首测 · `bvp_test_v1`

| 维度 | 定义 |
|------|------|
| **提取什么** | 问卷开放回答 → `bvp_candidate_id`, `memorability`, `understandability`, `purchase_intent`（1–5 或 null） |
| **成功标准** | 量表字段在域内或 null；解析率 ≥90% |
| **容忍度** | 非量表句 → null + review |
| **输入边界** | 问卷导出 CSV/JSON；非访谈录音 |

#### F-BRD-014 · 社会形象诊断 · `image_diag_v1`

抽取 `image_dimension`, `observed_score`, `expected_score`, `gap`, `sample_voice`。输入为已汇总调研+舆情摘要。

#### F-BRD-015 · App 体验审计 · `ux_audit_v1`

抽取 `feature_name`, `brand_consistency_score`, `issue_tags[]`, `severity`。输入为评审笔记文本/表。

#### F-BRD-017 · NPS 实时 NLP

单条开放反馈复用 `voc_entities_v1`；须保留可选 `nps` 数值字段（来自表单，非抽取）。

---

### 2.4 订单政策 / 渠道战区

#### F-OPS-004 · 销售政策解析 · `policy_parse_v1`

| 维度 | 定义 |
|------|------|
| **提取什么** | 政策原文 → `policy_id?`, `rebate_tiers[]{tier_name, threshold_qty, rebate_rate}`, `effective_from`, `effective_to`, `constraints[]` |
| **成功标准** | 档位数值解析准确 ≥90%；日期合法 |
| **容忍度** | 模糊档位 → review；禁止臆造费率 |
| **输入边界** | 政策 PDF **文本层**/MD；扫描件无 OCR 则拒收 |

#### F-OPS-011 · 标杆复制路径 · `benchmark_actions_v1`

抽取 `benchmark_dealer_id`, `actions[]{action, priority, evidence}`。输入为标杆案例纪要文本。成功：动作条数 ≥3 且非空；容忍改写同义。

#### F-WZ-004 · 导购人效 · `guide_efficacy_v1`

抽取 `guide_id`, `channel_account_id`, `eff_score`, `issues[]`, `suggestions[]`。输入为人效报表+短评文本。

---

### 2.5 制造品质

#### F-MFG-002 · PDA 绑定 · `pda_bind_v1`

| 维度 | 定义 |
|------|------|
| **提取什么** | 扫码/台账行 → `vin`, `frame_part_no`, `station_id`, `bound_at`, `operator_id` |
| **成功标准** | VIN/件号格式 100% 合法；绑定键完整 |
| **容忍度** | 无 |
| **输入边界** | PDA JSON/CSV 行；非自由叙述（叙述类转人工） |

#### F-MFG-006 · 追溯包 · `trace_package_v1`

抽取 `vin`, `batch_no`, `qc_pass`, `trace_package_uri`, `component_ids[]`。输入为放行记录结构化行+摘要。成功：VIN+qc_pass 必填。

---

### 2.6 产品 / 财经 / 人资 / 法务 / IT / 用户运营

#### F-PRD-001 · 竞品卡 · `competitor_card_v1`

抽取 `competitor_code`(虚构), `price_band`, `promotion_claim`, `reputation_tags[]`, `period`。输入：公开网页纯文本快照。成功率：字段非空率 ≥80%；禁止真实品牌名。

#### F-PRD-004 · 专利聚类 · `patent_cluster_v1`

抽取 `cluster_id`, `tech_theme`, `maturity_level(enum)`, `patent_ids[]`, `summary`。输入：专利摘要 JSON 列表。

#### F-FIN-001 · 三单匹配 · `tri_doc_match_v1`

| 维度 | 定义 |
|------|------|
| **提取什么** | 发票/合同/入库单文本 → `invoice_no`, `po_no`, `amount`, `currency`, `vendor_name`, `mismatch_fields[]` |
| **成功标准** | 单号/金额抽取准确 ≥95%；差异字段精确率 ≥85% |
| **容忍度** | OCR 噪声金额 ±0.01 可接受 |
| **输入边界** | 单据 OCR 文本或 JSON；影像原件归 Vision 前置 |

#### F-HR-002 · 岗位匹配 · `job_match_v1`

抽取 `candidate_id?`, `skill_tags[]`, `matched_job_ids[]`, `match_score`。输入：简历纯文本（合成）。PII 必须脱敏。

#### F-LEG-001 · 合同风险 · `contract_risk_v1`

抽取 `clause_id`, `risk_type`, `severity(P0-P2)`, `excerpt`, `suggestion`。输入：合同条款文本。成功：高风险条款漏报 ≤5%。

#### F-UO-006 · 续费意向 · `renew_intent_v1`

抽取 `customer_id`, `intent_level(high\|mid\|low)`, `intent_evidence`, `paid_intent_flag`。输入：外呼转写。与 Rule+LLM 分流衔接；Extraction 只出结构化意向。

#### F-UO-010 · FAQ 摘要 · `faq_digest_v1`

抽取 `question`, `answer_summary`, `source_feedback_ids[]`, `kb_domain`。输入：高频问题簇文本。

#### F-UO-011 · 分群特征 · `segment_feat_v1`

抽取 `segment_name`, `rules_or_features{}`, `size_estimate?`。输入：特征说明/SQL 注释/运营笔记（非替数仓）。

#### F-UO-015 · KOC 候选 · `koc_candidate_v1`

抽取 `user_id`, `koc_score`, `evidence_tags[]`。输入：社区互动宽表+短文。

#### F-UO-016 · UGC 文本审核 · `ugc_moderation_v1`

抽取 `content_id`, `violate_flag`, `violate_categories[]`, `severity`。图像部分归 Vision；本 Schema 仅文本。

#### F-IT-001 · 流程冗余 · `process_dup_v1`

抽取 `process_a`, `process_b`, `overlap_score`, `redundant_steps[]`。输入：流程说明 MD/BPMN 导出文本。

---

## 3. 校验与落盘约定

| 步骤 | 要求 |
|------|------|
| 1. validate | 输出必须通过对应 JSON Schema；失败不写库 |
| 2. 字典对齐 | 凡 `tag_*` 必须能在 `data/vocab/tag_vocabulary.json` 解析（Demo） |
| 3. 共享产出 | Demo 路径：`write_ai_output` → Store/`AIOutput` |
| 4. 文档位置 | 本契约：`docs/extraction/01-阶段一-输出Schema-成功标准-输入边界.md` |
| 5. 机器 Schema | `docs/extraction/schemas/*.json`（Demo 两个已落地；占位可按需补文件） |

---

## 4. 阶段一验收清单（Extraction）

- [x] 所有涉及部门/功能均有「提取什么 / 成功标准 / 输入边界」
- [x] Demo：`ticket_draft_v1`、`voc_entities_v1` 具备机器可读 Schema
- [x] 实现 `agents/extraction/` 控制环并挂 `ticket_fields`、`voc_entities`
- [x] 金标集（≥20 条填单 + ≥20 条 VoC）跑通准确率门槛（见阶段四评测报告）
- [x] Story1 可选路径：`extraction + voc_tagging` → `AIOutput`

---

## 5. 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-08-05 | 阶段一契约首版：全功能卡 + Demo 双 Schema |
