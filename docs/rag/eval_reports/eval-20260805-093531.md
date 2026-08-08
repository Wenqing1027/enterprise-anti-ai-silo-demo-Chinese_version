# RAG 金标评测报告 · 2026-08-05T09:35:31Z

- **结果**: `PASS`
- **用例数**: 15
- **耗时**: 51.03s

## 指标

| 指标 | 值 | 门槛 |
|------|----|------|
| 运行成功率 (`run_ok_rate`) | 1.0 | 1.0 |
| 金标文档召回 (`hit_doc_recall`) | 1.0 | 0.8 |
| 引用可见率 (`cite_present_rate`) | 1.0 | 1.0 |
| 关键词覆盖 (`keyword_hit_rate`) | 1.0 | 0.7 |
| 域隔离 (`domain_isolation_rate`) | 1.0 | 1.0 |
| 越域安全 (`cross_domain_safe_rate`) | 1.0 | 1.0 |

## 逐条

| id | skill | ok | doc_hit | kw | xdom | stop |
|----|-------|----|---------|----|------|------|
| RAG-REP-001 | repair_kb | True | True | True | None | cited_answer |
| RAG-REP-002 | repair_kb | True | True | True | None | cited_answer |
| RAG-REP-003 | repair_kb | True | True | True | None | cited_answer |
| RAG-REP-004 | repair_kb | True | True | True | None | cited_answer |
| RAG-REP-005 | repair_kb | True | True | True | None | cited_answer |
| RAG-POL-001 | policy_kb | True | True | True | None | cited_answer |
| RAG-POL-002 | policy_kb | True | True | True | None | cited_answer |
| RAG-POL-003 | policy_kb | True | True | True | None | cited_answer |
| RAG-POL-004 | policy_kb | True | True | True | None | cited_answer |
| RAG-HR-001 | hr_rules | True | True | True | None | cited_answer |
| RAG-HR-002 | hr_rules | True | True | True | None | cited_answer |
| RAG-HR-003 | hr_rules | True | True | True | None | cited_answer |
| RAG-XDOM-001 | repair_kb | True | None | True | True | no_hit_answered |
| RAG-XDOM-002 | policy_kb | True | None | True | True | cited_answer |
| RAG-XDOM-003 | hr_rules | True | None | True | True | no_hit_answered |
