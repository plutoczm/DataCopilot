# Changelog

## 0.1.0 - Module 1-15 Completion

### Module 1: Project Skeleton

- Created backend, frontend, tests, docs, scripts, data, Docker, model, and knowledge-base directories.
- Added project-local virtual environment bootstrap in the same style as Yolov26.

### Module 2: Configuration System

- Added `pydantic-settings` configuration.
- Supported `development`, `test`, and `production` environments.
- Added typed DeepSeek, OpenAI, Ollama, path, runtime, and logging settings.
- Validated all runtime paths under the project root.

### Module 3: Logging System

- Added structured JSON logging.
- Added rotating file handler.
- Added request ID and trace ID context.
- Integrated FastAPI request tracing.

### Module 4: Knowledge Base RAG

- Added document ingestion, chunking, retrieval, citation, and RAG services.
- Added TXT, Markdown, PDF, and DOCX loaders.
- Added embedding provider abstraction and BGE-M3 placeholder provider.
- Added grounded RAG prompt and structured citation model.

### Module 5: ChromaDB Integration

- Added vector store domain port.
- Added ChromaDB adapter with collection CRUD, document CRUD, metadata filters, similarity search, scored search, pagination, and persistence.
- Persisted vector data under `data/chromadb`.

### Module 6: DeepSeek Provider

- Added LLM provider domain port.
- Added DeepSeek async HTTP implementation.
- Supported chat, streaming, retries, timeouts, health checks, structured errors, usage tracking, and token counting.

### Module 7: FastAPI Backend

- Added FastAPI app, routes, schemas, dependencies, OpenAPI, global exception handlers, middleware, and health endpoints.
- Added document upload/list/delete, knowledge query, RAG stream, runtime config, root endpoint, docs, and OpenAPI.

### Module 8: Text2SQL

- Added schema parser, prompt builder, SQL validator, Text2SQL service, API schema, and route.
- Supported MySQL, Hive, Spark SQL, and ClickHouse.

### Module 9: SQL Review

- Added SQL parser, rule engine, SQL Review service, API schema, and route.
- Added risk scoring, issues, optimization suggestions, and LLM explanation support.

### Module 10: Log Analysis

- Not implemented yet.

### Module 11: Warehouse Designer

- Added warehouse design models, prompt builder, design service, and API route.
- Generated ODS, DWD, DWS, ADS, DIM, fact tables, relationships, DDL, metrics, data flow, and recommendations.

### Module 12: LangGraph Agent Router

- Added LangGraph agent graph, state, nodes, intent router, models, API schema, and routes.
- Supported RAG, Text2SQL, SQL Review, Warehouse Design, General Chat, Unknown, and Text2SQL plus SQL Review chained workflow.
- Updated Streamlit Chat into Agent Chat.

### Module 13: Streamlit Frontend

- Added frontend app, pages, components, API client, Dockerfile, and tests.
- Supported Agent Chat, Knowledge Base, Text2SQL, SQL Review, and Warehouse Designer pages.

### Module 14: Docker Compose Deployment

- Added production `docker-compose.yml`.
- Added `docker/.env.production`.
- Added optimized backend and frontend Dockerfiles.
- Added health checks, resource limits, bind mounts, optional Ollama profile, and deployment tests.

### Module 15: Integration Tests

- Added full integration test suite for RAG, Text2SQL, SQL Review, Warehouse Design, Agent Router, frontend/backend client integration, and frontend render smoke.
- Added `pytest-cov` dev dependency.
- Verified coverage above 85%.

## Current Verification

- Full test suite: `111 passed`.
- Coverage: `89.84%`.
