# 青枢出行 · 防 AI 孤岛平台 Demo（V2）

虚构智能电动车出行企业 **青枢出行（Qingshu Mobility）** 作品集 Demo。

平台统一治理 **4 类控制环 + 3 类工具**，业务部门以 **Skill** 挂载；通过共享语义与产出层，演示可治理的「防 AI 孤岛」。

本仓库为可运行参考实现，使用合成数据，不含真实客户信息与品牌。

## 平台控制环（4）

| 环 | 目录 | 状态 |
|----|------|------|
| Retrieve（检索） | `agents/rag/` | 已落地：`repair_kb` / `policy_kb` / `hr_rules` |
| Act（执行） | `agents/react/` | 已落地 |
| Extract（抽取） | `agents/extraction/` | 已落地：`ticket_fields` / `voc_*` |
| Plan（规划/闸门） | `agents/planning/` | 已落地：`renewal_plan`（Story2 闸门） |

工具治理三类：**Read · Knowledge · Write/Govern**（见 `shared/tools/`）。

总架构：[BLUEPRINT.md](./BLUEPRINT.md)  
设计决策：[docs/design-decisions.md](./docs/design-decisions.md)  
咨询叙事：[docs/consulting-narrative.md](./docs/consulting-narrative.md)

## 怎么跑

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 填入 DEEPSEEK_API_KEY

# CLI（Act · Story1）
python3 apps/cli.py --agent-type act --skill fill_ticket \
  --input data/seeds/story_1_fill_ticket.json

# CLI（Extract · Story1）
python3 apps/cli.py --agent-type extract --skill ticket_fields \
  --input data/seeds/story_1_ticket_fields.json

# CLI（Retrieve）
python3 apps/cli.py --agent-type retrieve --skill repair_kb \
  --input '{"query":"续航低于标称怎么排查？"}'

# CLI（Plan · Story2 闸门；须先有共享投诉标签）
python3 apps/cli.py --agent-type plan --skill renewal_plan \
  --input data/seeds/story_2_renewal_block.json

# 金标评测
python3 scripts/eval_extraction.py
python3 scripts/eval_rag.py

# Plan 冒烟（上游写标签 → 另跑闸门阻断）
python3 scripts/smoke_planning.py

# API（业务墙试跑 / 运维故障排查）
bash scripts/ensure_api.sh
# 业务 http://127.0.0.1:8000/business
# 运维 http://127.0.0.1:8000/ops
# OpenAPI /docs
```

## 架构要点（V2）

- **成品三件套**：Control Loops + Tools + Skills（一功能一 Skill）
- **平台管环与工具**：部门只交 Skill，不复制控制环与 DataFetcher
- **反孤岛在共享层**：标签字典、共享产出、能力目录，配合 Write/Govern 工具
- **跨功能经共享层另开运行**：`department_flows` 只作关系说明，不自动联跑、不做 Agent 互相对话

## 说明

本项目用于作品集展示平台化 Loops + Tools + Skills 的参考实现。  
不是已上线的企业中台，也不是多部门生产交付。
