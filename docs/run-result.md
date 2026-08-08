# 统一 RunResult（阶段 D）

> 版本：与 `apps/run_result.py` 中 `RUN_RESULT_VERSION` 同步  
> 真相源：各环 `POST /v1/*/runs` 与 `POST /v1/runs` 的响应经 `wrap_run_result` 归一化  
> 机读说明：`GET /v1/meta` → `run_result` / `run_result_version`

## 公共字段（前端主认）

| 字段 | 类型 | 说明 |
|------|------|------|
| `run_id` | string | 运行 ID |
| `control_loop` | string | `retrieve` \| `act` \| `extract` \| `plan` |
| `skill_id` | string | Skill |
| `ok` | bool | 是否成功 |
| `final_text` | string | 终答文本 |
| `steps` | array | 步骤 |
| `ai_output_ids` | string[] | 写出的共享产出 ID |
| `error` | string\|null | 失败时原因；成功多为 null |
| `extensions` | object | 环内其它字段袋 |

兼容别名：`final_answer` ≡ `final_text`（过渡期保留，新代码请用 `final_text`）。

## 分环扩展（顶层）

| control_loop | 字段 |
|--------------|------|
| extract | `payload` |
| retrieve | `citations` |
| plan | `gate`：`blocked` · `reason` · `tag_ids`（另含 `allow_outreach`） |
| act | （无强制顶层扩展；细节在 `extensions.success_flags`） |

## extensions 常见键

`stop_reason` · `feature_id` · `department_id` · `layout` · `tone_label` · `success_flags` · `plan`（Plan 短计划体）· `api_path` · `resolved_via`

## 验收

```bash
python3 scripts/smoke_run_result.py
```
