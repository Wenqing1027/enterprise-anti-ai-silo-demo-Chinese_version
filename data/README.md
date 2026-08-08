# data/ 合成数据说明

品牌：**青枢出行（Qingshu Mobility）**  
数据种子：`20260801`  
重建命令：`python scripts/generate_synthetic_data.py`

## 合规

- 全量合成，无真实客户 / 合同 / 工单录音
- VIN 一律 `QS0…` 前缀
- 手机号仅 `phone_masked`（中间四位 ****）
- 禁止拷贝任何真实客户或真实车企材料入库

## 目录

| 路径 | 内容 |
|------|------|
| `OBJECT_CATALOG.md` | 名词对象分类 |
| `vocab/field_glossary.json` | 跨部门字段统一释义 |
| `vocab/tag_vocabulary.json` | 标签字典 |
| `entities/*.json` | 结构化实体（含 `control_loop_aliases.json`、`tool_class_map.json`、`skill_loop_map.json`、`department_flows.json`） |
| `knowledge/**` | 非结构化长文本（源 md + `index.json`） |
| `knowledge/chunks.json` | RAG 切块产物（`scripts/build_kb_chunks.py`） |
| `knowledge/tfidf_index.json` | RAG TF-IDF 索引（`scripts/build_kb_index.py`） |
| `seeds/*.json` | Story1/2 演示种子 |
| `MANIFEST.json` | 规模统计与合规声明 |

切块 / 索引说明：`docs/rag/04-文档切块策略.md` · `docs/rag/05-索引库与检索器.md`。重建：

```bash
python scripts/build_kb_chunks.py
python scripts/build_kb_index.py
```

## 规模（本次）

```json
{
  "regions.json": 8,
  "orgs.json": 8,
  "dealers.json": 20,
  "stores.json": 40,
  "guides.json": 40,
  "skus.json": 50,
  "competitors.json": 4,
  "customers.json": 120,
  "vehicles.json": 142,
  "user_behaviors.json": 142,
  "renewals.json": 142,
  "orders.json": 80,
  "inventory.json": 50,
  "policies.json": 20,
  "color_plans.json": 60,
  "tickets.json": 120,
  "voc_feedback.json": 120,
  "telemetry.json": 40,
  "sales_metrics.json": 20,
  "dealer_health.json": 20,
  "retail_daily.json": 40,
  "campaigns.json": 2,
  "contents.json": 16,
  "outreach.json": 5,
  "quality_checks.json": 25,
  "inspections.json": 18,
  "finance_expense.json": 12,
  "alerts.json": 8,
  "store_dev.json": 8,
  "risks.json": 20,
  "capability_catalog.json": 6,
  "tag_vocabulary": 27,
  "knowledge_docs": 15,
  "field_glossary": 400
}
```
