# Roadmap

## Phase 1 Completed

DataPilot-AI now includes:

- Project skeleton and project-local virtual environment.
- Strongly typed configuration system with environment separation.
- Structured logging and request tracing.
- DeepSeek LLM provider.
- ChromaDB vector store adapter.
- Knowledge Base RAG pipeline.
- FastAPI backend.
- Text2SQL service.
- SQL Review service.
- Warehouse Designer.
- LangGraph Agent Router.
- Streamlit frontend.
- Docker Compose deployment.
- Integration tests and coverage reporting.

## Phase 2 Future

### Spark Integration

- Spark SQL execution connector.
- Spark plan parser.
- AQE and shuffle diagnostics.
- Skew detection and optimization recommendations.

### Hive Integration

- Hive metastore schema introspection.
- Partition health checks.
- Table lineage extraction.
- Hive DDL generation and validation.

### ClickHouse Integration

- ClickHouse schema crawler.
- Primary key and order key recommendations.
- Query rewrite suggestions for `PREWHERE`, projections, and materialized views.

### Kafka Integration

- Topic documentation assistant.
- Consumer lag diagnostics.
- Event schema registry integration.
- Streaming data quality checks.

### Flink Integration

- Flink SQL generation.
- State and checkpoint troubleshooting.
- Streaming job topology explanation.
- Windowing and watermark design assistant.

### Local LLM Support

- Ollama provider implementation.
- Local model routing.
- Offline demo profile.
- Privacy-focused enterprise deployment mode.

### GPU Inference

- GPU embedding generation.
- Local reranking support.
- Local LLM acceleration.
- Batch ingestion optimization.

## Phase 3 Ideas

- Authentication and role-based access.
- Workspace and tenant isolation.
- Evaluation framework for RAG and agent routing.
- WebSocket streaming.
- Async background ingestion jobs.
- CI Docker build and image publishing.
- Hosted demo environment.
