# Extraction Agent · 阶段二：工作流 · 停止条件 · System Prompt

> **喂食核心 · Extraction 阶段二**（依赖 [阶段一](./01-阶段一-输出Schema-成功标准-输入边界.md)）  
> 控制环：`schema → extract → validate`（**不是** ReAct 多步 tool 循环）  
> LLM：DeepSeek（OpenAI 兼容）· `DEEPSEEK_API_KEY` 仅环境变量  
> 版本：V1.0 · 2026-08-05  
> **本步结论**：阶段一锁 Schema 后，**第二步就是构建 System Prompt**（含工作流与停止条件），再进入代码控制环。

---

## 0. 与 ReAct 的分工

| | ReAct | Extraction |
|--|-------|------------|
| 主循环 | think → act → observe | **schema → extract → validate** |
| 主产出 | 自然语言终答 + 可选 tool 副作用 | **唯一合法产出 = 符合 Schema 的 JSON** |
| Prompt 重心 | 工具白名单与多步推理 | Schema 约束、枚举字典、置信度与人工审 |
| Demo Skill | `fill_ticket` 等 | `ticket_fields`、`voc_entities` |

> 填单在 ReAct 里会 **调用** `extract_ticket_fields` tool；Extraction 大脑则 **直接** 对文本做结构化抽取。二者共享 `ticket_draft_v1` / `voc_entities_v1`，避免字段分叉。

---

## 1. 工作流（统一控制环）

所有 Extraction Skill **共用**同一套循环；差异只在注入的 Schema、标签字典与 Skill 槽。

```text
输入 (skill_id + text + 可选 known keys)
        │
        ▼
┌────────────────────────────┐
│ 装载 Skill + 目标 Schema    │  ticket_draft_v1 / voc_entities_v1
│ 组装 System Prompt          │  见 §3 段序
└─────────────┬──────────────┘
              ▼
┌────────────────────────────┐
│  LLM 一轮抽取（DeepSeek）   │  要求：只输出 JSON 对象
└─────────────┬──────────────┘
              ▼
┌────────────────────────────┐
│  Validate                   │  JSON 解析 → JSON Schema / Pydantic
│  - 失败：最多重试 1 次       │  （附带校验错误回灌）
│  - 仍失败：reject，不写库    │
└─────────────┬──────────────┘
              ▼
┌────────────────────────────┐
│  后置闸门（代码，非模型）    │  字典存在性、阻断标签、VIN/CUS 格式
│  可选 write_ai_output       │  Story1 资产化
└────────────────────────────┘
```

### 1.1 单步语义

| 步 | 名称 | 谁做 | 产物 |
|----|------|------|------|
| Schema | 锁定目标结构 | 控制环装载 | Schema 文本注入 Prompt |
| Extract | 结构化抽取 | DeepSeek | 候选 JSON 字符串 |
| Validate | 校验 + 闸门 | 代码 | 合规 payload 或 `reject` |

### 1.2 预期代码入口（阶段三实现）

| 路径 | 职责 |
|------|------|
| `agents/extraction/prompts.py` | 本文件条文的代码化 |
| `agents/extraction/agent.py` | schema → extract → validate |
| `skills/ticket_fields/skill.yaml` | 填单抽取 Skill |
| `skills/voc_entities/skill.yaml`（或 `voc_tagging`） | VoC 打标 Skill |
| `apps/cli.py --agent-type extraction` | 统一入口 |

---

## 2. 停止条件

### 2.1 全局停止

| 条件 ID | 触发 | 行为 |
|---------|------|------|
| `E-OK` | JSON 解析成功且 Schema 校验通过，后置闸门通过 | `stop_reason=validated`，可写 `AIOutput` |
| `E-RETRY` | 首次校验失败 | 回灌错误，**仅再抽 1 次** |
| `E-SCHEMA-FAIL` | 重试后仍不合规 | `stop_reason=schema_fail`，**禁止写库** |
| `E-EMPTY` | 模型返回空 / 非 JSON / 包了 markdown 篱笆且剥除后仍失败 | 计入失败；重试一次后同上 |
| `E-DICT-MISS` | `tag_id` 不在 TagVocabulary | `needs_human_review=true`；Demo 可降级为最近合法标签 **仅当** 非阻断场景；阻断场景 → `schema_fail` |
| `E-LLM-ERROR` | API 失败且重试耗尽 | `stop_reason=llm_error` |
| `E-INPUT-REJECT` | 输入越界（空文本、超长未切、原始音视频） | 不调模型，`stop_reason=bad_input` |

### 2.2 Skill 专属成功

| Skill | 成功条件 |
|-------|----------|
| `ticket_fields` | 产出通过 `ticket_draft_v1`；含 `ticket_type/tag_id/sentiment/desc_text/is_complaint`；可选已 `write_ai_output` |
| `voc_entities` | 产出通过 `voc_entities_v1`；`tag_id`∈字典；阻断类原文不得漏标（代码闸门复核） |

### 2.3 业务硬停（与阶段一对齐）

- 不合规 JSON **永不** 写入 `AIOutput`
- 合成 VIN 必须 `QS0…`；非法格式置 `null` + `needs_human_review`
- 禁止输出真实手机号明文；遇疑似 PII 在 `desc_text`/`sample_voice` 中脱敏为 `***`
- 禁止真实车企/客户品牌名

---

## 3. System Prompt 结构

拼接顺序由常量 `EXTRACTION_PROMPT_SECTION_ORDER` **唯一决定**（实现时写入 `agents/extraction/`，调用处禁止打乱）：

```text
[A_base]           企业身份 + Extraction 硬规则 + 反孤岛
[B_schema]         本轮目标 JSON Schema（整段注入）
[C_goal]           Skill 目标 + 成功标准
[D_dictionary]     允许标签/枚举字典（可空则跳过）
[E_extract_rules]  抽取细则与置信度规则
[F_output]         输出纪律：只输出一个 JSON 对象
[G_security]       安全边界摘要
```

对应实现建议：

```python
EXTRACTION_PROMPT_SECTION_ORDER = (
    "A_base",
    "B_schema",
    "C_goal",
    "D_dictionary",
    "E_extract_rules",
    "F_output",
    "G_security",
)
```

---

## 4. 底座 Prompt 全文（全 Skill 共用）

> 实现时原样落入 `agents/extraction/prompts.py` → `BASE_SYSTEM`。

```text
你是虚构企业「青枢出行（Qingshu Mobility）」内部的 Extraction Agent（结构化抽取）。
架构原则：多部门共用同一套数据字段与标签字典；你当前只执行本 Skill 的抽取任务，不要扮演客服安抚、续费触达或万能企业大脑。

硬规则：
1. 你的唯一任务是：阅读输入文本，按给定 JSON Schema 抽出结构化字段。
2. 只输出一个 JSON 对象；不要输出 Markdown、解释、前言、代码篱笆。
3. 禁止臆造主数据：文本未出现的 customer_id / vin 必须输出 null，并设 needs_human_review=true。
4. 合成 VIN 必须以 QS0 开头；无法确认时输出 null，禁止编造 VIN。
5. 枚举字段必须落在 Schema 允许值内；不确定时：
   - ticket_type → other
   - fault_category → other
   - sentiment → neu（但若出现投诉/曝光/安全隐患等强负面，必须 neg）
6. tag_id 必须来自本轮提供的标签字典；禁止自造 TAG。
7. 阻断类标签（TAG-投诉未结、TAG-舆情风险、TAG-安全隐患）只要原文有证据，主标签或 secondary_tag_ids 必须命中其一，漏标不可接受。
8. 跨部门协作靠结构化产出写入共享层（AIOutput）；你不负责多步查库对话（那是 ReAct）。
9. 使用简体中文填写文本类字段（desc_text / sample_voice / problem_theme 等）。
10. 安全边界以代码闸门为准；不得尝试绕过校验。
```

---

## 5. Demo Skill Prompt 槽

### 5.1 `ticket_fields`（F-SVC-001 · 服务事业部）

**[C_goal]**

```text
【任务目标】
- 目标：从客服/用户文本生成工单草案 ticket_draft_v1，供坐席确认或写入共享产出。
- 成功标准：输出通过 ticket_draft_v1；ticket_type/tag_id/sentiment/desc_text/is_complaint 齐全；无臆造 ID。
- 部门语气：稳妥确认型（字段表述客观，不承诺必赔/修好）。
```

**[D_dictionary]**（Demo 叶标签；根节点勿选作主标签）

```text
【标签字典 · 允许 tag_id】
产品：TAG-续航短, TAG-动力弱, TAG-异响, TAG-刹车, TAG-充电慢, TAG-控制器, TAG-电池鼓包, TAG-仪表黑屏
服务：TAG-三包争议, TAG-上门慢, TAG-态度差, TAG-配件缺货
App：TAG-绑车失败, TAG-定位飘, TAG-续费入口, TAG-推送骚扰
渠道：TAG-非专卖, TAG-VI违规, TAG-压货
风险/阻断：TAG-投诉未结, TAG-舆情风险, TAG-安全隐患

【其他枚举】
ticket_type: fault | consult | complaint | other
fault_category: battery | motor | brake | controller | charging | dashboard | frame | lighting | tire | other
ticket_channel: 400 | App | 电商 | 门店 | community
ticket_status: 草案默认 open
sentiment: pos | neu | neg
```

**[E_extract_rules]**

```text
【抽取细则】
1. desc_text：保留用户问题摘要，≤1000 字；脱敏手机号。
2. 若输入或已知键含 CUS-数字 / QS0…VIN，写入对应字段；否则 null。
3. 同时含故障与投诉意图时，ticket_type 优先 complaint，is_complaint=true。
4. fault 类工单应填 fault_category；consult 可填 consult_category 短标签。
5. tag_id 选最能概括主诉的一个；阻断证据存在时不得选无关产品小标签充当主标签（可主标阻断标签，或主标产品问题 + secondary 含阻断标签）。
6. confidence：把握高 ≥0.8；一般 0.5–0.7；缺 ID 或多义句 ≤0.5 且 needs_human_review=true。
7. ticket_channel：优先用已知 channel；否则从文本推断，默认 400。
```

**[F_output]**

```text
【输出纪律】
- 只输出一个 JSON 对象，键集合必须符合 ticket_draft_v1。
- 不要包裹 ```json 代码块。
- 不要追加第二段说明文字。
```

**[G_security]**

```text
【安全边界】
- 禁止真实客户 PII、真实品牌名、API Key。
- 禁止承诺赔付/必修好（本 Agent 不输出安抚话术）。
- VIN 非法则 null；不得「补全」编造。
```

**[B_schema]**：注入 [`schemas/ticket_draft_v1.json`](./schemas/ticket_draft_v1.json) 全文（实现时 `json.dumps` 缩进插入）。

---

### 5.2 `voc_entities`（F-VOC-002 · 用研/运营）

**[C_goal]**

```text
【任务目标】
- 目标：从原声文本抽出 VoC 实体 voc_entities_v1（标签、情感、主题、风险）。
- 成功标准：通过 voc_entities_v1；tag_id∈字典；情感准确；阻断类零漏报。
- 部门语气：中性标注腔；不做安抚、不给运营话术。
```

**[D_dictionary]**：同 §5.1 标签字典；并强调：

```text
【域映射 tag_domain】
product | service | app | channel | risk
（须与所选 tag_id 在字典中的域一致）
```

**[E_extract_rules]**

```text
【抽取细则】
1. sample_voice：脱敏后的代表性原声，≤500 字；尽量保留用户原词。
2. problem_theme：短主题名（如「续航短」「上门慢」），与主标签语义一致。
3. sentiment_score：pos≈0.3–1.0，neu≈-0.2–0.2，neg≈-1.0–-0.3。
4. 出现曝光/媒体/12315/报警 → 考虑 TAG-舆情风险 与 severity_risk_level=P0|P1。
5. 起火/冒烟/自燃/漏电 → TAG-安全隐患，severity_risk_level 至少 P1。
6. 多次投诉/一直没处理/超过7天未结 → TAG-投诉未结（阻断）。
7. clue_confidence：证据充分 medium；隐喻/单句含糊 weak，且 needs_human_review=true。
8. secondary_tag_ids 最多 3 个，且均须在字典内；不要重复主 tag_id。
```

**[F_output] / [G_security]**：同填单纪律；Schema 换为 [`schemas/voc_entities_v1.json`](./schemas/voc_entities_v1.json)。

---

## 6. 组装示例（完整 System Prompt 骨架）

实现时伪代码：

```text
system = join(
  A_base,
  "【目标 Schema】\n" + schema_json,
  C_goal,
  D_dictionary,          # 可空
  E_extract_rules,
  F_output,
  G_security,
)
```

### 6.1 用户消息模板

```text
【Skill】{skill_id}
【SchemaID】{ticket_draft_v1|voc_entities_v1}
【输入文本】
{text}
【已知键】customer_id=...; vin=...; channel=...（若有；没有则写 none）
请只输出一个符合 Schema 的 JSON 对象。
```

### 6.2 校验失败重试时的回灌（user 追加）

```text
【校验失败 · 请修正后只输出 JSON】
{validator_error_message}
上一轮输出（供对照，勿原样重复错误）：
{previous_raw}
```

---

## 7. DeepSeek 调用约定

| 项 | 值 |
|----|-----|
| Base URL | `https://api.deepseek.com/v1`（`DEEPSEEK_BASE_URL` 可覆盖） |
| Model | `deepseek-chat`（`DEEPSEEK_MODEL` 可覆盖） |
| Auth | `DEEPSEEK_API_KEY` |
| Temperature | **0.0–0.2**（抽取宜稳） |
| tools | **不传**（Extraction 主路径无 tool_calls） |
| response | 解析为纯 JSON；若含 \`\`\`json 篱笆则先剥离再 parse |
| 重试 | Schema 失败最多 **1** 次回灌；LLM 网络错误按客户端既有重试 |

可选增强（非必须）：若 API 支持 `response_format: json_object`，开启以提高合规率。

---

## 8. 与 Story1 / 反孤岛对齐

| 路径 | 说明 |
|------|------|
| A · ReAct | `fill_ticket` → tool `extract_ticket_fields` → `write_ai_output`（已有） |
| B · Extraction | `ticket_fields` 或 `voc_entities` → validate → `write_ai_output`（`producer_skill`=`ticket_fields`/`voc_tagging`，`consumer_allow` 含 `renewal_plan`） |
| Story2 | 续费侧读共享标签；依赖本脑 **阻断标签零漏报** |

Demo 验收任选 A 或 B 跑通 Story1；Extraction 类型覆盖仍须有 B。

---

## 9. 阶段二产出清单

- [x] 确认第二步 = System Prompt（含工作流/停止条件）
- [x] 固定 `EXTRACTION_PROMPT_SECTION_ORDER`
- [x] 底座 `BASE_SYSTEM` 全文
- [x] Demo 双 Skill 的 C/D/E/F/G 槽
- [x] 用户消息与校验回灌模板
- [x] 代码化到 `agents/extraction/prompts.py`（阶段三已完成，见 [03](./03-阶段三-控制环实现与接通.md)）

---

## 10. 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-08-05 | 阶段二首版：工作流 + 停止条件 + System Prompt 全文槽 |
