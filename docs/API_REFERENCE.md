# API 接口参考

默认地址：`http://127.0.0.1:8000`。Swagger 位于 `/docs`，OpenAPI JSON 位于 `/openapi.json`。

所有 JSON 请求使用 `Content-Type: application/json`。参数校验失败返回统一错误结构：

```json
{
  "error": {
    "code": "validation_error",
    "message": "请求参数校验失败",
    "details": []
  }
}
```

## 健康与配置

### `GET /health`

检查应用、LLM Provider 和向量库。

### `GET /api/v1/config/runtime`

返回不含密钥的运行环境、默认 Provider、Embedding 模型和能力开关。`capabilities.read_only_query_execution` 表示只读执行能力是否在配置中启用。

## 知识库

### `POST /api/v1/knowledge/documents`

上传 PDF、DOCX、TXT 或 Markdown 文档，使用 `multipart/form-data`。

### `GET /api/v1/knowledge/documents`

查看当前登记的已摄取文档。

### `DELETE /api/v1/knowledge/documents/{document_id}`

删除文档登记信息和对应向量分块。

### `POST /api/v1/knowledge/query`

直接执行 RAG 查询。

```bash
curl -X POST http://127.0.0.1:8000/api/v1/knowledge/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Spark AQE 有什么作用？",
    "collection_name": "knowledge_base",
    "top_k": 5,
    "retrieval_mode": "hybrid",
    "score_threshold": 0.2
  }'
```

关键参数：

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `question` | string | 必填 | 用户问题 |
| `collection_name` | string | `knowledge_base` | 知识库集合 |
| `top_k` | integer | `5` | 最终召回数量，范围 1-20 |
| `retrieval_mode` | string | `hybrid` | `hybrid` 或 `vector` |
| `metadata_filter` | object | `null` | ChromaDB 元数据过滤 |
| `score_threshold` | number | `null` | 最低相关度 |

## RAG 流式对话

### `POST /api/v1/chat/stream`

响应类型 `text/event-stream`，包含 token、citations、done 等事件。

## 统一智能体

### `GET /api/v1/agent/tools`

查看结构化工具名称、说明和 Pydantic JSON Schema。

### `POST /api/v1/agent/chat`

自动路由 RAG、Text2SQL、SQL Review、数仓设计或通用对话。数据库 Query Execution **不属于 Agent Tool**，避免自主链路隐式触发数据库资源操作。

### `POST /api/v1/agent/chat/stream`

智能体 SSE 接口。

### `DELETE /api/v1/agent/sessions/{session_id}`

清除指定会话的进程内短期记忆和摘要。

## Text2SQL

### `POST /api/v1/text2sql`

```bash
curl -X POST http://127.0.0.1:8000/api/v1/text2sql \
  -H "Content-Type: application/json" \
  -d '{
    "question": "统计最近30天各区域GMV",
    "engine": "sqlite",
    "schema_context": "orders(order_id integer, customer_id integer, order_amount numeric, created_at timestamp)",
    "use_rag": false
  }'
```

支持：`sqlite`、`mysql`、`hive`、`spark_sql`、`clickhouse`。

响应包含：

- `sql`；
- `explanation`；
- `optimization_suggestions`；
- `confidence`；
- `validation.is_valid / issues`；
- `token_usage`；
- provider/model 等 metadata。

Text2SQL 只生成候选 SQL，不自动触发数据库执行。

## SQL Review

### `POST /api/v1/sql-review`

返回风险等级、质量分数、问题列表、优化建议和可选 LLM 解释。

### `POST /api/v1/sql-review/generate-and-review`

在单个接口中先 Text2SQL，再进行 SQL Review。

## 受治理只读查询执行

该能力默认关闭：

```text
DATACOPILOT_QUERY_EXECUTION__ENABLED=false
```

### `GET /api/v1/query-execution/datasources`

返回**非敏感**的数据源元数据，不返回数据库路径或凭据。

响应示例：

```json
{
  "execution_enabled": true,
  "datasources": [
    {
      "name": "retail_demo",
      "kind": "sqlite",
      "available": true,
      "description": "Configured read-only datasource"
    }
  ]
}
```

### `POST /api/v1/query-execution`

显式执行一条受治理只读 SQL。

```bash
curl -X POST http://127.0.0.1:8000/api/v1/query-execution \
  -H "Content-Type: application/json" \
  -d '{
    "datasource": "retail_demo",
    "sql": "SELECT order_id, order_amount FROM orders ORDER BY order_id LIMIT 20",
    "max_rows": 20
  }'
```

请求字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `datasource` | string | 配置中的白名单数据源名 |
| `sql` | string | 单条 `SELECT/WITH` SQL |
| `max_rows` | int/null | 客户端期望上限；最终仍受服务端 `MAX_ROWS` 限制 |

执行前后会经过：

1. feature flag；
2. datasource whitelist；
3. `ReadOnlySQLPolicy`；
4. SQLite `mode=ro` + `PRAGMA query_only=ON`；
5. timeout/deadline；
6. server row cap；
7. query audit。

响应示例：

```json
{
  "query_id": "0a7353d7-...",
  "datasource": "retail_demo",
  "columns": ["order_id", "order_amount"],
  "rows": [{"order_id": 101, "order_amount": 198.0}],
  "row_count": 1,
  "truncated": false,
  "elapsed_ms": 0.82
}
```

执行审计记录 SQL SHA-256，而不是把原始 SQL 或凭据塞进专用审计字段。

常见错误码：

| HTTP | error.code | 场景 |
| --- | --- | --- |
| `400` | `query_rejected` | SQL 被只读策略拒绝 |
| `404` | `datasource_not_found` | 数据源不在白名单 |
| `408` | `query_timeout` | 查询超过 deadline |
| `503` | `query_execution_disabled` | 执行能力未开启 |
| `503` | `datasource_unavailable` | 配置的数据源不可用 |

## 数仓设计

### `POST /api/v1/warehouse-design`

响应包含 ODS、DWD、DWS、ADS、维度表、事实表、指标、关系、DDL、数据流和设计建议。

## 评测 Runner

评测目前作为 repo 内 runner，而不是线上公共 API：

```bash
python examples/retail_analytics/evaluate_text2sql.py
```

输出 `data/evaluation/retail_text2sql_report.json`，区分 generation、validation、execution、schema hallucination、latency、token 和 safety 指标。

## 通用状态码

| 状态码 | 说明 |
| --- | --- |
| `200` | 成功 |
| `201` | 文档创建成功 |
| `400` | 业务规则/只读策略拒绝 |
| `404` | 资源或数据源不存在 |
| `408` | 受治理查询超时 |
| `422` | Pydantic 参数校验失败 |
| `500` | 内部错误 |
| `502` | LLM Provider 调用失败 |
| `503` | 可选能力关闭或依赖不可用 |
