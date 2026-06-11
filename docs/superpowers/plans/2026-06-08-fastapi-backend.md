# FastAPI Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose DataPilot-AI capabilities through production-grade FastAPI endpoints with typed schemas, dependency injection, middleware, exception handling, OpenAPI metadata, and tests.

**Architecture:** API routes contain no business logic and depend on application services and domain ports through FastAPI dependencies. Concrete DeepSeek, ChromaDB, RAG, logging, and settings wiring is centralized in reusable dependency providers and the app factory.

**Tech Stack:** FastAPI, Pydantic v2, httpx TestClient, pytest, SSE streaming.

---

### Task 1: API Contract Tests

**Files:**
- Create: `tests/api/test_fastapi_backend.py`

- [x] **Step 1: Write failing tests**

Cover `/health`, `/api/v1/config/runtime`, document upload/list/delete, direct RAG query, SSE streaming, validation errors, and consistent exception response format.

- [x] **Step 2: Run tests to verify failure**

Run: `.venv/bin/python -m pytest tests/api -v`

Expected: FAIL until FastAPI app, routes, schemas, and dependencies exist.

### Task 2: API Schemas, Dependencies, Routes, App

**Files:**
- Create: `backend/app/presentation/api/schemas/common.py`
- Create: `backend/app/presentation/api/schemas/health.py`
- Create: `backend/app/presentation/api/schemas/knowledge.py`
- Create: `backend/app/presentation/api/dependencies/providers.py`
- Create: `backend/app/presentation/api/routes/health.py`
- Create: `backend/app/presentation/api/routes/config.py`
- Create: `backend/app/presentation/api/routes/knowledge.py`
- Create: `backend/app/presentation/api/routes/chat.py`
- Create: `backend/app/presentation/api/router.py`
- Modify: `backend/app/main.py`
- Modify: `backend/requirements.txt`

- [x] **Step 1: Add FastAPI runtime dependencies**

Add `fastapi`, `uvicorn`, and `python-multipart` to backend requirements.

- [x] **Step 2: Implement schemas and providers**

Create typed request/response schemas and dependency providers for settings, vector store, LLM, RAG, ingestion, document registry, and runtime capabilities.

- [x] **Step 3: Implement routes**

Create health, config, knowledge, and chat streaming routes.

- [x] **Step 4: Implement app factory**

Wire router, exception handlers, logging/request tracing middleware, timing middleware, OpenAPI tags, and Swagger UI.

### Task 3: Verification

- [x] **Step 1: Run Module 7 tests**

Run: `.venv/bin/python -m pytest tests/api -v`

Expected: PASS.

- [x] **Step 2: Run full test suite**

Run: `.venv/bin/python -m pytest -v`

Expected: PASS.

### Self-Review

- Spec coverage: Covers listed endpoints, validation, response schemas, DI, health checks, logging/request tracing, timing, OpenAPI metadata, SSE, exception handling, and tests.
- Placeholder scan: No TODO or TBD markers are present.
- Type consistency: API schemas map to existing RAG, LLM, vector-store, and settings models.
