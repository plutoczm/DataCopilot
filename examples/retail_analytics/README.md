# 零售经营分析 Demo

这个目录提供一个可复现的企业数据分析场景，用于验证从业务口径、Schema 自动发现、Text2SQL、安全校验、只读执行到 Golden Result Evaluation 的完整链路。

## 场景

假设一家零售平台希望让运营人员用自然语言查询订单、客户、商品和退款数据。典型问题包括：

- 最近 30 天各区域 GMV；
- 各获客渠道客单价；
- 品类销售额 Top10；
- 整体退款率；
- 退款金额最高的区域。

## 文件

- `schema.sql`：orders / customers / products / order_items / refunds Schema；
- `seed.sql`：固定演示数据；
- `setup_demo_db.py`：生成项目内 SQLite 演示数据库；
- `metric_definitions.md`：可上传到 RAG 的 GMV、退款率、客单价等业务口径；
- `questions.json`：5 条业务问题，并为每题提供 `golden_sql` 结果 Oracle；
- `safety_cases.json`：只读允许/拒绝策略样本；
- `run_demo.py`：调用 datasource-driven Text2SQL API；
- `evaluate_text2sql.py`：运行生成、校验、执行、Golden Result 与 Safety benchmark；
- `check_benchmark_report.py`：对 benchmark JSON 执行发布质量门禁。

## 1. 初始化演示数据源

```bash
python examples/retail_analytics/setup_demo_db.py --force
```

然后启动 backend。Text2SQL 可直接使用 `retail_demo` datasource 自动发现 Schema，不需要手工复制 DDL。

## 2. 运行交互 Demo

```bash
python examples/retail_analytics/run_demo.py
```

如果后端不在默认地址，可通过 `BACKEND_URL` 指定。

## 3. 运行可复现 Benchmark

查询执行默认关闭。需要运行 Execution / Golden Result / Safety benchmark 时，应显式开启受治理只读执行，并使用演示数据源，而不是连接任意生产数据库。

```bash
python examples/retail_analytics/evaluate_text2sql.py
python examples/retail_analytics/check_benchmark_report.py
```

报告会区分 Generation Success、Valid SQL、Execution Success、Schema Hallucination、Business Result Accuracy、Latency、Token Usage 和 Safety 指标。

每份新报告还记录：

- `benchmark_version`；
- `questions_sha256`；
- `schema_sha256`；
- `safety_cases_sha256`；
- `benchmark_fingerprint`。

这些字段用于确认候选报告与 accepted baseline 是否基于同一套评测输入，避免把不同数据集的指标直接比较。

## RAG 业务口径

把 `metric_definitions.md` 上传到知识库后，可在 Text2SQL 请求中设置 `use_rag=true`。类似“退款率”“客单价”这类业务概念会优先使用检索到的企业口径，而不是仅依赖模型先验。

## 安全边界

执行能力是独立边界而不是 Agent 自主工具：默认 feature flag 关闭；启用后仍要求服务端 datasource、只读 SQL policy、SQLite read-only mode、timeout、max rows、Schema fingerprint precondition 与审计信息。演示能力不等价于可直接连接任意生产数据库。
