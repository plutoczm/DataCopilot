# 零售经营分析 Demo

这个目录提供一个可复现的 Text2SQL 业务场景，用于证明项目不仅能展示组件，还能围绕真实业务问题组织 Schema、指标口径、API 调用和评测问题。

## 场景

假设一家零售平台希望让运营人员用自然语言查询订单、客户、商品和退款数据。典型问题包括：

- 最近 30 天各区域 GMV；
- 各获客渠道客单价；
- 品类销售额 Top10；
- 整体退款率；
- 退款金额最高的区域。

## 文件

- `schema.sql`：演示数据库 Schema；
- `metric_definitions.md`：可上传到知识库的业务指标口径；
- `questions.json`：可重复执行的 Text2SQL 评测问题；
- `run_demo.py`：调用后端 API 并输出 SQL、置信度和校验结果。

## 运行

先启动后端并配置可用的大模型，然后执行：

```bash
python examples/retail_analytics/run_demo.py
```

如果后端不在默认地址：

```bash
BACKEND_URL=http://127.0.0.1:8000 python examples/retail_analytics/run_demo.py
```

## RAG 业务口径演示

把 `metric_definitions.md` 上传到知识库后，可在 Text2SQL API 中设置 `use_rag=true`。这样类似“退款率”“客单价”这类业务概念会优先使用检索到的企业口径，而不是让模型自行猜测。

## 安全边界

当前主链路负责生成与审核 SQL，不默认连接生产数据库执行任意查询。Text2SQL 校验器只接受单条只读 `SELECT/WITH` 查询，并拒绝常见 DDL/DML。真实生产接入数据库时仍应额外使用只读账号、查询超时、扫描量限制和审计日志。
