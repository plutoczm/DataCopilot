# API Reference

Base URL:

```text
http://localhost:8000
```

Interactive Swagger UI:

```text
http://localhost:8000/docs
```

## Health

### GET `/health`

Checks application, LLM provider, and vector store status.

```bash
curl http://localhost:8000/health
```

Example response:

```json
{
  "service": "DataPilot-AI",
  "status": "ok",
  "environment": "production",
  "llm_provider": {
    "provider": "deepseek",
    "ok": true,
    "api_key_configured": true,
    "reachable": true,
    "model_available": true,
    "model": "deepseek-chat",
    "message": "DeepSeek provider is healthy"
  },
  "vector_store": {
    "status": "ok",
    "collection_name": "knowledge_base",
    "document_count": 12
  }
}
```

## Runtime Config

### GET `/api/v1/config/runtime`

Returns public runtime capabilities without secrets.

```bash
curl http://localhost:8000/api/v1/config/runtime
```

## Knowledge Base

### POST `/api/v1/knowledge/documents`

Uploads and indexes a document.

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/documents \
  -F "collection_name=knowledge_base" \
  -F "domain=spark" \
  -F "tags=spark,aqe" \
  -F "file=@spark_aqe.md"
```

Example response:

```json
{
  "document_id": "doc-1",
  "filename": "spark_aqe.md",
  "file_type": "md",
  "domain": "spark",
  "collection_name": "knowledge_base",
  "chunk_count": 8
}
```

### GET `/api/v1/knowledge/documents`

Lists indexed documents.

```bash
curl http://localhost:8000/api/v1/knowledge/documents
```

### DELETE `/api/v1/knowledge/documents/{document_id}`

Deletes a document and associated vectors.

```bash
curl -X DELETE http://localhost:8000/api/v1/knowledge/documents/doc-1
```

### POST `/api/v1/knowledge/query`

Runs a direct RAG query.

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How does Spark AQE reduce shuffle cost?",
    "collection_name": "knowledge_base",
    "top_k": 5
  }'
```

Example response:

```json
{
  "answer": "Spark AQE can optimize shuffle partitions and join strategies at runtime.",
  "citations": [
    {
      "document_name": "spark_aqe.md",
      "chunk_reference": "spark_aqe.md#chunk-0",
      "similarity_score": 0.96,
      "source_metadata": {
        "document_id": "doc-1",
        "filename": "spark_aqe.md",
        "domain": "spark",
        "chunk_index": 0
      }
    }
  ],
  "metadata": {
    "collection_name": "knowledge_base",
    "retrieved_count": 1
  },
  "token_usage": {
    "prompt_tokens": 120,
    "completion_tokens": 80,
    "total_tokens": 200
  }
}
```

## Streaming Chat

### POST `/api/v1/chat/stream`

Streams a RAG chat response as Server Sent Events.

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"Explain Hive partition pruning","collection_name":"knowledge_base"}'
```

SSE events:

```text
event: token
data: {"text":"..."}

event: citations
data: {"citations":[...]}

event: done
data: {"metadata":{...}}
```

## Agent

### POST `/api/v1/agent/chat`

Classifies intent and invokes the correct workflow.

```bash
curl -X POST http://localhost:8000/api/v1/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "统计最近7天活跃用户并检查SQL",
    "engine": "hive",
    "schema_context": "dwd_user_behavior_detail(user_id bigint, dt string)"
  }'
```

Example response:

```json
{
  "intent": "TEXT2SQL_SQL_REVIEW",
  "result": {
    "generated_sql": {
      "sql": "SELECT COUNT(DISTINCT user_id) AS active_users FROM dwd_user_behavior_detail WHERE dt >= date_sub(current_date, 7)"
    },
    "review": {
      "risk_level": "LOW",
      "score": 94
    }
  },
  "routing_path": ["classify_intent", "text2sql", "sql_review", "format_response"],
  "final_response": "Generated SQL...",
  "metadata": {
    "tool_usage": {
      "text2sql": 1,
      "sql_review": 1
    }
  },
  "token_usage": {
    "prompt_tokens": 20,
    "completion_tokens": 15,
    "total_tokens": 35
  }
}
```

### POST `/api/v1/agent/chat/stream`

Streams agent metadata, response text, structured result, and completion event.

```bash
curl -N -X POST http://localhost:8000/api/v1/agent/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"设计电商订单数仓"}'
```

## Text2SQL

### POST `/api/v1/text2sql`

Generates validated SQL.

```bash
curl -X POST http://localhost:8000/api/v1/text2sql \
  -H "Content-Type: application/json" \
  -d '{
    "question": "统计最近7天活跃用户",
    "engine": "hive",
    "schema_context": "dwd_user_behavior_detail(user_id bigint, dt string)"
  }'
```

## SQL Review

### POST `/api/v1/sql-review`

Reviews SQL quality, performance, and risk.

```bash
curl -X POST http://localhost:8000/api/v1/sql-review \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT * FROM dwd_order_detail",
    "engine": "spark",
    "include_llm_explanation": true
  }'
```

Example response:

```json
{
  "risk_level": "HIGH",
  "score": 42,
  "issues": [
    {
      "code": "select_star",
      "title": "SELECT * detected",
      "description": "Avoid scanning unnecessary columns.",
      "severity": "MEDIUM",
      "suggestion": "Select required columns only.",
      "category": "general"
    }
  ],
  "optimization_suggestions": ["Select required columns only."],
  "llm_explanation": "The query scans more data than needed.",
  "engine": "spark_sql",
  "token_usage": {
    "prompt_tokens": 50,
    "completion_tokens": 30,
    "total_tokens": 80
  },
  "metadata": {}
}
```

## Warehouse Design

### POST `/api/v1/warehouse-design`

Generates layered warehouse design, DDL, metrics, and recommendations.

```bash
curl -X POST http://localhost:8000/api/v1/warehouse-design \
  -H "Content-Type: application/json" \
  -d '{
    "requirement": "设计电商订单分析数仓",
    "use_rag": true
  }'
```

Example response shape:

```json
{
  "requirement": "设计电商订单分析数仓",
  "ods": [],
  "dwd": [],
  "dws": [],
  "ads": [],
  "dim": [],
  "fact_tables": [],
  "ddl": [
    {
      "table_name": "dwd_order_detail",
      "layer": "DWD",
      "sql": "CREATE TABLE dwd_order_detail (...) PARTITIONED BY (dt STRING) STORED AS PARQUET;"
    }
  ],
  "metrics": [
    {
      "name": "GMV",
      "definition": "Gross merchandise volume",
      "calculation_logic": "SUM(pay_amount)",
      "business_meaning": "Measures transaction scale."
    }
  ],
  "recommendations": ["Partition Strategy: partition all fact and summary tables by dt."]
}
```
