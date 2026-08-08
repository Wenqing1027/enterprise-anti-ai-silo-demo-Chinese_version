# 名词对象分类（结构化）

> 青枢出行（Qingshu Mobility）· Demo 合成数据目录  
> 口径：按「名词对象 / 实体」分类，不按部门拆库；各部门消费同一套 ID。

## A. 主数据（Master）

| 对象 | 文件 | 说明 |
|------|------|------|
| Org / Region | `entities/orgs.json`, `entities/regions.json` | 组织树与行政区 |
| Dealer | `entities/dealers.json` | 一代经销商 |
| Store | `entities/stores.json` | 门店 |
| Guide | `entities/guides.json` | 导购 |
| Customer | `entities/customers.json` | C 端客户 / 身份 |
| Vehicle | `entities/vehicles.json` | 车辆（VIN 一律 `QS0…` 合成） |
| SKU | `entities/skus.json` | 车型颜色 SKU |
| Competitor | `entities/competitors.json` | 竞品快照（虚构品牌） |

## B. 交易与库存（Transactional）

| 对象 | 文件 | 说明 |
|------|------|------|
| Order | `entities/orders.json` | 提货/订单 |
| Inventory | `entities/inventory.json` | 仓/店库存 |
| Policy | `entities/policies.json` | 返利政策与结算摘要 |
| ColorPlan | `entities/color_plans.json` | 颜色排产计划 |
| SalesMetric | `entities/sales_metrics.json` | 销量/签约达成切片 |
| Health | `entities/dealer_health.json` | 一代经营健康指数 |

## C. 服务与声音（Service / VoC）

| 对象 | 文件 | 说明 |
|------|------|------|
| Ticket | `entities/tickets.json` | 工单 |
| VoC | `entities/voc_feedback.json` | 反馈/调研切片 |
| Telemetry | `entities/telemetry.json` | 车联告警与里程电量 |
| Renewal | `entities/renewals.json` | 车联续费池 |
| UserBehavior | `entities/user_behaviors.json` | App 行为 / RFM |

## D. 零售营销与触达

| 对象 | 文件 | 说明 |
|------|------|------|
| Retail | `entities/retail_daily.json` | 门店零售日报切片 |
| Campaign | `entities/campaigns.json` | 活动 |
| Content | `entities/contents.json` | 矩阵/内容账号表现 |
| Outreach | `entities/outreach.json` | 触达渠道能力 |

## E. 质量 / 巡检 / 财经（扩展主数据）

| 对象 | 文件 | 说明 |
|------|------|------|
| Quality | `entities/quality_checks.json` | OBD/质检记录 |
| Inspection | `entities/inspections.json` | 门店巡检 |
| Finance | `entities/finance_expense.json` | 三单匹配样例 |
| Alert | `entities/alerts.json` | 经营预警 |
| StoreDev / Risk | `entities/store_dev.json`, `entities/risks.json` | 开店与风控 |

## F. 共享语义与 AI 资产

| 对象 | 文件 | 说明 |
|------|------|------|
| TagVocabulary | `vocab/tag_vocabulary.json` | 统一标签字典 |
| FieldGlossary | `vocab/field_glossary.json` | 跨部门字段统一释义 |
| CapabilityCatalog | `entities/capability_catalog.json` | Skill 能力目录骨架 |
| Knowledge | `knowledge/**` | 非结构化长文本（维修/政策/制度） |

## G. 演示种子

| 对象 | 文件 | 说明 |
|------|------|------|
| Story seeds | `seeds/story_1_fill_ticket.json`, `seeds/story_2_renewal_block.json` | Story1/2 输入 |

## 关联键（全库统一）

`customer_id` · `vin` · `dealer_id` · `store_id` · `sku_id` · `ticket_id` · `order_id` · `tag_id` · `campaign_id` · `oneid`
