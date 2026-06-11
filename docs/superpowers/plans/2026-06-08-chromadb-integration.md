# ChromaDB Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a replaceable vector-store abstraction and a persistent ChromaDB infrastructure adapter with document CRUD, metadata filtering, similarity search, pagination, and tests.

**Architecture:** Domain code owns document/chunk entities and the vector-store port. ChromaDB details stay under `backend/app/infrastructure/vectorstore`, so future Milvus, Weaviate, Elasticsearch Vector, or PGVector adapters can replace ChromaDB without changing business logic.

**Tech Stack:** Python 3.12, pydantic domain models, ChromaDB persistent client, pytest.

---

### Task 1: Vector Store Contract Tests

**Files:**
- Create: `tests/infrastructure/test_chromadb_store.py`

- [x] **Step 1: Write failing tests**

Cover collection CRUD, document CRUD, update/delete, similarity search, score search, metadata filtering, pagination, collection stats, embedding dimension errors, not-found errors, and persistence across adapter instances.

- [x] **Step 2: Run tests to verify failure**

Run: `.venv/bin/python -m pytest tests/infrastructure/test_chromadb_store.py -v`

Expected: FAIL until ChromaDB dependency and adapter files exist.

### Task 2: Domain Entities And Vector Store Port

**Files:**
- Create: `backend/app/domain/entities/document.py`
- Create: `backend/app/domain/entities/chunk.py`
- Create: `backend/app/domain/entities/__init__.py`
- Create: `backend/app/domain/ports/vector_store.py`

- [x] **Step 1: Define domain entities**

Add typed document and chunk metadata models independent of ChromaDB.

- [x] **Step 2: Define vector-store protocol**

Expose collection CRUD, document CRUD, searches, metadata filtering, pagination, and stats.

### Task 3: ChromaDB Adapter

**Files:**
- Create: `backend/app/infrastructure/vectorstore/__init__.py`
- Create: `backend/app/infrastructure/vectorstore/models.py`
- Create: `backend/app/infrastructure/vectorstore/exceptions.py`
- Create: `backend/app/infrastructure/vectorstore/chromadb_store.py`
- Modify: `backend/requirements.txt`
- Modify: `.env.example`

- [x] **Step 1: Add ChromaDB dependency**

Add `chromadb` and refresh `.venv`.

- [x] **Step 2: Implement adapter**

Persist to `settings.paths.chromadb_dir`, validate vectors, support batch insert/delete, pagination, lazy collection access, metadata filters, similarity search, score search, document fetch, update, delete, collection stats, and structured exceptions.

### Task 4: Verification

- [x] **Step 1: Run Module 5 tests**

Run: `.venv/bin/python -m pytest tests/infrastructure/test_chromadb_store.py -v`

Expected: PASS.

- [x] **Step 2: Run full test suite**

Run: `.venv/bin/python -m pytest -v`

Expected: PASS.

### Self-Review

- Spec coverage: Covers Clean Architecture separation, replaceable vector-store abstraction, persistent project-local storage, metadata schema, CRUD, search, filters, batching, pagination, lazy loading, and required exceptions.
- Placeholder scan: No TODO or TBD markers are present.
- Type consistency: Tests import the same public names exported by the vectorstore infrastructure package.
