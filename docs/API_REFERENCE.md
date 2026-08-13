# API 接口参考

默认地址：`http://127.0.0.1:8000`。Swagger 位于 `/docs`，OpenAPI JSON 位于 `/openapi.json`。

除 `/health` 外，API 位于受保护 Router 下。开启鉴权后使用：

```text
X-API-Key: <reader|analyst|admin key>
```

参数校验失败返回统一错误结构：

```json
{
  "error": {
    "code": "validation_error",
    "message": "请求参数校验失败",
    "details": []
  }
}
```

## 健康、身份与配置

### `GET /health`

检查应用、LLM Provider 和向量库。

### `GET /api/v1/auth/me`

返回当前 principal、role 与鉴权状态，不返回 API key。

### `GET /api/v1/config/runtime`

返回不含密钥的运行环境、默认 Provider、Embedding 模型和能力开关。

## 知识库

### `POST /api/v1/knowledge/documents`

上传 PDF、DOCX、TXT 或 Markdown 文档，使用 `multipart/form-data`。

### `GET /api/v1/knowledge/documents`

查看持久化 Registry 中的已摄取文档。

### `DELETE /api/v1/knowledge/documents/{document_id}`

删除文档登记信息和对应向量分块。

### `POST /api/v1/knowledge/query`

执行 RAG 查询。支持 collection、top-k、hybrid/vector retrieval、metadata filter 和 score threshold。

## RAG 流式对话

### `POST /api/v1/chat/stream`

响应类型 `text/event-stream`，包含 token、citations、done 等事件。

## 统一智能体

### `GET /api/v1/agent/tools`

查看结构化工具名称、说明和 Pydantic JSON Schema。

### `POST /api/v1/agent/chat`

自动路由 RAG、Text2SQL、SQL Review、数仓设计或通用对话。Query Execution **不属于 Agent Tool**，避免自主链路隐式访问数据库资源。

### `POST /api/v1/agent/chat/stream`

智能体 SSE 接口。

### `DELETE /api/v1/agent/sessions/{session_id}`

清除指定会话的进程内短期记忆和摘要。

## Text2SQL

### `POST /api/v1/text2sql`

推荐使用 **Datasource 模式**：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/text2sql \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $DATACOPILOT_API_KEY" \
  -d '{
    "question": "统计最近30天各区域GMV",
    "datasource": "retail_demo",
    "use_rag": true
  }'
```

服务端通过 `SchemaCatalog` 自动发现表结构并绑定数据源 SQL Engine。生成 metadata 包含：

- `schema_source=datasource`；
- `datasource`；
- `schema_fingerprint`；
- `schema_table_count_discovered`。

也可以使用手工 Schema：

```json
{
  "question": "统计最近30天各区域GMV",
  "engine": "hive",
  "schema_context": "orders(order_id bigint, customer_id bigint, amount decimal(18,2), dt string)",
  "use_rag": false
}
```

约束：

- `datasource` 与 `schema_context` 互斥；
- Datasource 模式下引擎由数据源决定；若客户端额外提供不一致的 `engine`，请求会被拒绝；
- 手工模式未指定 `engine` 时保持默认 Hive 行为；
- Text2SQL 只生成和校验候选 SQL，不自动触发数据库执行。

支持引擎：`sqlite`、`mysql`、`hive`、`spark_sql`、`clickhouse`。

响应包含 SQL、解释、优化建议、confidence、validation、token usage 与 provenance metadata。

## SQL Review

### `POST /api/v1/sql-review`

返回风险等级、质量分数、问题列表、优化建议和可选 LLM 解释。

### `POST /api/v1/sql-review/generate-and-review`

在单个接口中先 Text2SQL，再执行 SQL Review。

## 数据源元数据与受治理只读执行

### `GET /api/v1/query-execution/datasources`

返回非敏感数据源元数据：名称、类型、物理可用状态，以及全局 `execution_enabled`。

注意：`available=true` 表示数据源可访问，**不代表模型 SQL 已获准执行**。Schema discovery 与 execution feature flag 是两个不同边界。

响应示例：

```json
{
  "execution_enabled": false,
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

### `GET /api/v1/query-execution/datasources/{datasource}/schema`

需要至少 `reader` 角色。该接口只读取用于 Text2SQL 的非凭据 Schema Snapshot，不开启任意 SQL 执行能力。

```bash
curl http://127.0.0.1:8000/api/v1/query-execution/datasources/retail_demo/schema \
  -H "X-API-Key: $DATACOPILOT_API_KEY"
```

响应：

```json
{
  "datasource": "retail_demo",
  "engine": "sqlite",
  "schema_context": "CREATE TABLE customers (...);\n\nCREATE TABLE orders (...);",
  "table_count": 5,
  "fingerprint": "<sha256>"
}
```

Fingerprint 描述“本次生成基于哪一版 Schema”；它不是授权令牌，也不包含数据库凭据。

### `POST /api/v1/query-execution`

需要至少 `analyst` 角色。执行能力默认关闭：

```text
DATACOPILOT_QUERY_EXECUTION__ENABLED=false
```

请求：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/query-execution \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $DATACOPILOT_API_KEY" \
  -d '{
    "datasource": "retail_demo",
    "sql": "SELECT order_id, order_amount FROM orders ORDER BY order_id LIMIT 20",
    "max_rows": 20,
    "expected_schema_fingerprint": "<sha256 returned by Text2SQL>"
  }'
```

`expected_schema_fingerprint` 可选，但 Datasource Text2SQL 的 UI 和 benchmark 会自动传入。执行服务会在运行 SQL 前重新读取当前 Schema：

- fingerprint 一致：继续执行只读策略与数据库查询；
- fingerprint 不一致：返回 `409 schema_drift`，要求重新生成和审核 SQL。

这用于防止生成与执行之间发生 Schema drift / TOCTOU。调用方自己提交的人工 SQL 可以不传 fingerprint，但仍必须经过完整只读策略和数据库权限边界。

执行路径包含：

1. execution feature flag；
2. datasource whitelist；
3. 可选 Schema fingerprint precondition；
4. `ReadOnlySQLPolicy`；
5. SQLite `mode=ro` + `PRAGMA query_only=ON`；
6. progress-handler deadline；
7. server row cap；
8. Query ID / actor / datasource / SQL SHA-256 / status / latency audit。

常见错误码：

| HTTP | error.code | 场景 |
| --- | --- | --- |
| `400` | `query_rejected` | SQL 被只读策略拒绝 |
| `401` | - | API key 缺失或无效 |
| `403` | - | role 不满足接口要求 |
| `404` | `datasource_not_found` | 数据源未配置 |
| `408` | `query_timeout` | 查询超过 deadline |
| `409` | `schema_drift` | 当前 Schema 与生成时 fingerprint 不一致 |
| `503` | `query_execution_disabled` | 执行能力未开启 |
| `503` | `datasource_unavailable` | 数据源不可用 |

## 数仓设计

### `POST /api/v1/warehouse-design`

响应包含 ODS、DWD、DWS、ADS、维度表、事实表、指标、关系、DDL、数据流和设计建议。

## Text2SQL Benchmark Runner

评测作为仓库内 runner，不暴露为线上公共 API：

```bash
python examples/retail_analytics/evaluate_text2sql.py
python examples/retail_analytics/evaluate_text2sql.py --use-rag
```

鉴权开启时：

```bash
DATACOPILOT_API_KEY=<analyst-key> python examples/retail_analytics/evaluate_text2sql.py
```

Runner 自身也使用 Datasource 模式，因此评测链路覆盖真实 Schema discovery，而不是另外维护一份只供 benchmark 使用的 Prompt 输入。

每个零售 case 包含 `golden_sql`。Runner 会：

1. 调用 Text2SQL；
2. 记录生成时 Schema fingerprint；
3. 校验生成 SQL；
4. 使用相同 fingerprint precondition 执行生成 SQL；
5. 在同一 Schema version 上执行 Golden SQL；
6. 比较结果集；
7. 输出 `business_result_accuracy`。

报告还区分 generation、validation、execution、table recall、schema hallucination、latency、token 与 safety 指标。`Execution Success` 不等于业务正确率。

报告默认写入：

```text
data/evaluation/retail_text2sql_report.json
```

## 通用状态码

| 状态码 | 说明 |
| --- | --- |
| `200` | 成功 |
| `201` | 文档创建成功 |
| `400` | 业务规则/只读策略拒绝 |
| `401` | 未认证 |
| `403` | 权限不足 |
| `404` | 资源或数据源不存在 |
| `408` | 受治理查询超时 |
| `409` | Schema precondition 冲突 |
| `422` | Pydantic 参数校验失败 |
| `500` | 内部错误 |
| `502` | LLM Provider 调用失败 |
| `503` | 可选能力关闭或依赖不可用 |
