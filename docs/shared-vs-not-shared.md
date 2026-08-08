# 平台管什么 / 不管什么

> 版本：V2.0 · 2026-08-06  
> 替代旧「共用 vs 不共用」短表；详见 [设计决策](./design-decisions.md) · [BLUEPRINT](../BLUEPRINT.md)

---

## 平台统一管理（发版 · 白名单 · 审计口径）

| 对象 | 说明 |
|------|------|
| **4 控制环** | Retrieve / Act / Extract / Plan 的实现与版本 |
| **3 类工具** | Read · Knowledge · Write/Govern；唯一 ToolRegistry |
| **DataFetcher** | 唯一数据访问实现 |
| **共享资产** | 统一 ID/模型、标签字典、`AIOutput`、CapabilityCatalog |
| **组合契约格式** | `department_flows` 字段与 `via` 约定 |
| **run / 日志格式** | 便于跨环对账（Demo 级） |

---

## 业务部门自建（平台不代写业务）

| 对象 | 说明 |
|------|------|
| **Skill** | **一功能一 Skill**；目标、成功条件、语气、tools 白名单、schema/索引槽 |
| **本部门功能清单** | 挂哪些 Skill；flows 仅申报共享依赖（非联跑） |
| **业务话术与策略** | 例如客服安抚 ≠ 电销话术（禁止混挂同一 Skill） |

---

## 明确不共用 / 禁止

| 禁止 | 原因 |
|------|------|
| 各部门复制控制环代码 | 平台环必须唯一实现 |
| 各部门私有 DataFetcher / 私有 tool 实现 | 孤岛与口径漂移 |
| Agent 互聊 / Agent→Agent 管道 | 难治理；跨功能只经共享产出、另开运行 |
| 把「共用 Agent 人设」当反孤岛 | 对象错位（见 DD-02） |
| 单 Orchestrator 替代四环或联跑全部 Skill | 滑向万能大脑 |

---

## 速查对照

```text
平台：Loops(4) + Tools(3类) + Store/语义
部门：Skills(N) + 申报的 flows
跨部门：只读/写 AIOutput 与统一标签
```
