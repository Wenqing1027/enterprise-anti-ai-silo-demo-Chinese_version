# ReAct Agent · 模块三：工作流 + 停止条件 + System Prompt

> **喂食核心 · 模块三**（依赖 [模块一](./01-模块一-背景-跨部门功能-语气.md) · [模块二](./02-模块二-分部门工具箱.md)）  
> LLM：**DeepSeek**（OpenAI 兼容 API）· key 仅环境变量 `DEEPSEEK_API_KEY`，禁止入库  
> 版本：V1.0 · 2026-08-02

---

## 1. 工作流（统一控制环）

所有部门 Skill **共用**同一套 ReAct 循环；差异只在 System Prompt 槽与 `allowed_tools`。

```text
输入 (skill_id + user_input + 可选 customer_id/vin)
        │
        ▼
┌───────────────────┐
│ 装载 Skill 配置    │  YAML：tone / goal / stop / tools 白名单
│ 组装 System Prompt │  底座提示 + 部门语气 + 工具说明
└─────────┬─────────┘
          ▼
┌───────────────────┐
│  LLM（DeepSeek）   │  messages + tools(JSON Schema)
└─────────┬─────────┘
          │
     ┌────┴────┐
     │         │
  tool_calls  纯文本终答
     │         │
     ▼         ▼
┌──────────────────┐
│ ToolRegistry.call │  Act + Observe
└─────────┬────────┘
          │ observation 写回 messages；step += 1
          └──────► 回到 LLM（直到停止）
```

### 1.1 单步语义

| 步 | 名称 | 谁做 | 产物 |
|----|------|------|------|
| Think | 推理 | DeepSeek | `tool_calls` 或最终自然语言 |
| Act | 行动 | `ToolRegistry` | `ToolResult` |
| Observe | 观察 | 控制环 | 把结果拼进下一轮 user/tool 消息 |

### 1.2 代码入口

| 路径 | 职责 |
|------|------|
| `shared/llm/client.py` | DeepSeek 客户端 |
| `agents/react/agent.py` | ReAct 控制环 |
| `skills/<id>/skill.yaml` | 目标 / 语气 / 停止 / 工具白名单 |
| `apps/cli.py --agent-type react` | 统一入口 |

```bash
export DEEPSEEK_API_KEY=...   # 或写入本地 .env（已 gitignore）
python apps/cli.py --agent-type react --skill fill_ticket \
  --input data/seeds/story_1_fill_ticket.json
```

---

## 2. 停止条件

### 2.1 全局停止（所有 Skill）

| 条件 ID | 触发 | 行为 |
|---------|------|------|
| `S-MAX-STEPS` | `step >= max_steps`（默认 8） | 强制结束，返回已收集证据 + `stop_reason=max_steps` |
| `S-FINAL` | 模型本轮无 tool_calls，仅文本 | 正常结束，`stop_reason=final` |
| `S-TOOL-DENY` | 连续 2 次 `TOOL_NOT_ALLOWED` | 结束，提示越权，`stop_reason=tool_denied` |
| `S-EMPTY` | 连续 2 次空/无效 tool 参数 | 结束，`stop_reason=bad_args` |
| `S-LLM-ERROR` | API 失败且重试耗尽 | 结束，`stop_reason=llm_error` |

### 2.2 Skill 专属成功停止

| Skill | 成功条件 | 说明 |
|-------|----------|------|
| `fill_ticket` | 已成功调用 `write_ai_output` 且 payload 含 `customer_id`+`tag_id`（或 ticket 字段） | Story1 验收 |
| `shared_write` | 已成功 `write_ai_output` | 资产写入完成 |
| `crm_lookup` | 至少完成 1 次主数据查询且模型给出汇总 | 查询闭环 |
| `channel_ops` | 至少完成健康/预警类查询且给出「数字+异常+下一步」 | 看板型闭环 |

成功停止实现（与 max_steps 不打架）：

1. 成功条件由 `skill.success_when` 机器判定。  
2. `max_steps` **只**循环带 tools 的工具轮。  
3. 成功后 `break` 出工具循环，**另开** 1 次终答调用（`tools=None`）。  
4. 未成功时跑满 max_steps → `max_steps`，不再多给带 tools 的一轮。  
5. 终答轮仍 tool_calls → `success_forced`。  

### 2.3 业务硬停

详见 [模块四](./04-模块四-安全限制与边界.md)：触达阻断、合成 VIN、PII/密钥、Skill `security` 槽等。

---

## 3. System Prompt 结构

拼接顺序由常量 `PROMPT_SECTION_ORDER` **唯一决定**（见 `agents/react/skill_schema.py`），不可在调用处打乱：

```text
[A_base]          企业身份 + ReAct 规则 + 反孤岛规则
[B_tone]          模块一风格标签与禁用项
[C_goal]          本 Skill 一句话目的 + 成功标准
[C2_system_extra] Skill 补充步骤（可空则跳过）
[D_tools]         仅可调用白名单；禁止编造 tool 结果
[E_output]        终答时对用户/坐席可见的结构（可空则跳过）
[F_security]      安全边界摘要（模块四追加，由 skill.security 生成）
```

`skill.yaml` 字段契约见 [`skills/SCHEMA.md`](../../skills/SCHEMA.md)。安全细则见 [模块四](./04-模块四-安全限制与边界.md)。

### 3.1 [A] 底座（全 Skill 共用）

见 `agents/react/prompts.py` → `BASE_SYSTEM`：

- 你是青枢出行（Qingshu Mobility）内部 ReAct Agent  
- 多部门共用手脚；你当前只代表 **本 Skill 部门角色**  
- 必须通过 tool 获取事实；禁止臆造客户/车辆/库存/政策数字  
- 跨 Skill 协作靠 `write_ai_output` / `read_ai_outputs`，不假装能调其他部门私有库  
- 合成数据 VIN 以 `QS0` 开头  

### 3.2 [B]+[C]+[E] 按 Skill（摘要）

完整条文在各 `skills/*/skill.yaml` 的 `system_extra`；下表供喂食对照。

| Skill | 语气（模块一） | 任务目标摘要 | 终答结构 |
|-------|----------------|--------------|----------|
| `fill_ticket` | 稳妥确认型 | 查主数据→抽工单字段→建议标签→**写入共享产出** | 复述问题 / 草案字段 / 已写入 output_id / 下一步 |
| `crm_lookup` | 结论优先型 | 按 ID 查齐客户·车·单·库存并汇总 | 结论三行内 + 关键字段 |
| `channel_ops` | 经营看板型 | 查健康/预警/巡检，给动作 | 数字 / 异常点 / 下一步 |
| `shared_write` | 中性系统腔 | 将 payload 资产化写入 | output_id + consumer_allow |

### 3.3 用户消息模板

```text
【Skill】{skill_id}
【输入】{text 或结构化 JSON}
【已知键】customer_id=... vin=...（若有）
请在工具白名单内完成任务；满足成功条件后给出最终答复。
```

---

## 4. DeepSeek 调用约定

| 项 | 值 |
|----|-----|
| Base URL | `https://api.deepseek.com/v1` |
| Model | `deepseek-chat`（可用 `DEEPSEEK_MODEL` 覆盖） |
| Auth | `DEEPSEEK_API_KEY` |
| Tool calling | OpenAI compatible `tools` / `tool_calls` |
| 解析契约 | `agents/react/tool_calls.py`（arguments 为 JSON 字符串） |
| Temperature | 默认 `0.2`（填单/查数宜稳） |

本地配置：

```bash
# .env（已在 .gitignore，勿提交）
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
```

---

## 5. 与 Story1 的对齐

| 步骤 | 期望 |
|------|------|
| 1 | `log_step` 记录开始（可选） |
| 2 | `get_customer` / `get_vehicle` 校验 ID |
| 3 | `extract_ticket_fields` + `suggest_voc_tags` |
| 4 | `write_ai_output`（producer=`fill_ticket`，consumer 含 `renewal_plan`） |
| 5 | 稳妥确认型终答；`stop_reason=success|final` |

---

## 6. 模块三完成标准（自检）

- [x] 统一 ReAct 工作流文档化  
- [x] 全局 + Skill 专属停止条件  
- [x] System Prompt 五段结构 + 各 Skill 条文  
- [x] DeepSeek 客户端与 `agents/react` 控制环落地  
- [x] CLI 可跑 `fill_ticket` Story1  

---

## 修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-08-02 | 模块三：工作流 / 停止条件 / Prompt + DeepSeek 实现 |
