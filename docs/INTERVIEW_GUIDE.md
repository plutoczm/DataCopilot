# Interview Guide

DataPilot-AI is an AI Agent Platform for Data Engineering. This document helps explain the project in resumes, interviews, and demos.

## Project Background

Data engineering work often requires switching between documents, SQL generation, query review, warehouse modeling, and platform-specific best practices. DataPilot-AI unifies these workflows behind an AI agent that can classify user intent and call the right tool automatically.

## Business Value

- Reduces repeated manual effort for SQL writing and review.
- Helps data engineers search technical knowledge and internal documentation.
- Accelerates warehouse design from business requirements.
- Provides a demo-ready AI agent platform for data engineering interviews.
- Uses replaceable provider interfaces so enterprise deployments can switch LLMs and vector databases.

## Architecture Decisions

### Clean Architecture

The project separates presentation, application, domain, and infrastructure layers. Business logic depends on domain ports such as `LLMProvider` and `VectorStore`, so DeepSeek, OpenAI, Ollama, ChromaDB, Milvus, or PGVector can be swapped without rewriting core workflows.

### Why LangGraph

LangGraph is used for explicit agent workflow orchestration. Compared with a single prompt-based router, the graph makes routing paths observable, testable, and extensible. It supports multi-step workflows such as Text2SQL followed by SQL Review.

### Why ChromaDB

ChromaDB is lightweight, local-first, and simple to deploy for demos and early production validation. The code depends on a vector store port, so future migration to Milvus, Weaviate, Elasticsearch Vector, or PGVector is isolated.

### Why FastAPI

FastAPI provides async support, Pydantic v2 validation, OpenAPI generation, dependency injection, and strong test ergonomics through TestClient. It is a good fit for production APIs and interview demos.

### Why Streamlit

Streamlit makes the product demonstrable quickly while preserving backend boundaries. The frontend calls only FastAPI APIs, so it does not access ChromaDB, DeepSeek, files, or internal services directly.

### Why DeepSeek

DeepSeek provides cost-effective LLM capabilities and OpenAI-style chat APIs. The provider implementation includes async HTTP requests, streaming, retries, timeouts, health checks, and usage tracking.

## Challenges and Solutions

| Challenge | Solution |
| --- | --- |
| Avoiding provider lock-in | Domain ports for LLM and vector store |
| Making agent routing testable | Rule-based intent classifier plus LangGraph graph |
| Preventing hallucination in RAG | Grounded prompt requiring retrieved context and citations |
| Supporting interviews and demos | Streamlit UI plus Docker Compose deployment |
| Keeping tests stable | Mock providers and integration fixtures instead of live LLM calls |
| Protecting host resources | Docker Compose CPU and memory limits |

## Performance

- Batch vector insert and delete are supported by the vector store adapter.
- ChromaDB persistence is kept under project-local data directories.
- FastAPI uses async endpoints and async LLM provider calls.
- Health checks expose degraded provider or vector store states.
- SQL Review includes deterministic rules, avoiding unnecessary LLM calls for core risk detection.

## Scalability

Current deployment is suitable for single-server demos and small-team use. Future scaling paths:

- Move ChromaDB to managed vector storage or Milvus.
- Add database schema introspection services for Hive, Spark, and ClickHouse.
- Add job queues for large document ingestion.
- Add provider registry for OpenAI, Ollama, and local LLM inference.
- Add auth, workspace isolation, and tenant-aware collections.

## Future Evolution

- Spark and Hive execution plan analysis.
- ClickHouse query rewrite suggestions.
- Kafka/Flink streaming pipeline assistant.
- GPU-backed embedding and local LLM inference.
- Evaluation harness for RAG quality and SQL correctness.

## Common Interview Questions

### 1. What problem does this project solve?

It unifies common data engineering AI workflows: knowledge search, SQL generation, SQL review, warehouse modeling, and agent routing. Instead of separate tools, users ask one agent, and the system chooses the workflow automatically.

### 2. How is the architecture organized?

It uses Clean Architecture. FastAPI and Streamlit are presentation. RAG, Text2SQL, SQL Review, Warehouse Design, and Agent are application services. Domain ports define LLM and vector store interfaces. Infrastructure implements DeepSeek, ChromaDB, loaders, and embeddings.

### 3. Why not call DeepSeek directly from business logic?

Direct calls would create provider lock-in. The application layer depends on `LLMProvider`, so switching to OpenAI, Ollama, or local LLM only requires another infrastructure adapter.

### 4. How does the agent decide which tool to use?

The agent uses a deterministic intent router for stable behavior and LangGraph for workflow execution. It supports RAG, Text2SQL, SQL Review, Warehouse Design, General Chat, Unknown, and a chained Text2SQL plus SQL Review workflow.

### 5. How do you prevent RAG hallucination?

The RAG prompt requires answers to use retrieved context only, state uncertainty when context is insufficient, avoid inventing technical facts, and include citations with document name, chunk reference, score, and metadata.

### 6. How does Text2SQL ensure quality?

It parses schema context, builds engine-specific prompts, requires structured JSON from the LLM, validates generated SQL against schema/rules, and returns confidence plus optimization suggestions.

### 7. What does SQL Review check?

It detects risks such as `SELECT *`, missing filters, partition-awareness issues, expensive joins, shuffle-heavy patterns, Cartesian joins, nested subqueries, and engine-specific performance problems.

### 8. Why use Docker Compose?

Docker Compose makes the project deployable with one command on Ubuntu 20.04. It includes backend, frontend, ChromaDB, optional Ollama, health checks, resource limits, and project-local persistence.

### 9. How did you test it?

The project includes unit tests, API tests, infrastructure tests, deployment tests, and integration tests. Coverage is verified with `pytest-cov` and currently exceeds the 85% target.

### 10. What would you improve next?

I would add Spark/Hive/ClickHouse live metadata integration, async ingestion jobs, auth, workspace isolation, local LLM support, GPU inference, and evaluation metrics for agent routing and RAG answer quality.

## Demo Script

1. Start Docker Compose or local backend/frontend.
2. Open Streamlit.
3. Upload a Spark AQE document in Knowledge Base.
4. Ask the Agent Chat: `什么是Spark AQE`.
5. Ask: `统计最近7天活跃用户并检查SQL`.
6. Ask: `设计电商订单分析数仓`.
7. Show Swagger UI and tests/coverage report.
