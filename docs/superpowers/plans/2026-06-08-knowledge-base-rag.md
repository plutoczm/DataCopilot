# Knowledge Base RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-grade RAG pipeline for document ingestion, chunking, embedding, vector storage, retrieval, citations, and grounded answer generation.

**Architecture:** Application RAG services depend on the domain `VectorStore` and `LLMProvider` ports plus an embedding protocol. Infrastructure provides document loaders and a BGE-M3-compatible embedding provider adapter. DeepSeek and ChromaDB are not imported by application RAG services.

**Tech Stack:** Python 3.12, pydantic models, pytest, optional pypdf/python-docx readers, deterministic tests with fake embedding/LLM/vector dependencies.

---

### Task 1: RAG Contract Tests

**Files:**
- Create: `tests/rag/test_document_loaders.py`
- Create: `tests/rag/test_rag_pipeline.py`

- [x] **Step 1: Write failing tests**

Cover TXT/Markdown/PDF/DOCX loaders, chunking, embedding generation, ingestion into vector store, top-k retrieval, metadata filters, score threshold, citation generation, and end-to-end RAG answer generation.

- [x] **Step 2: Run tests to verify failure**

Run: `.venv/bin/python -m pytest tests/rag -v`

Expected: FAIL until RAG services and loaders exist.

### Task 2: Application RAG Services

**Files:**
- Create: `backend/app/application/rag/__init__.py`
- Create: `backend/app/application/rag/models.py`
- Create: `backend/app/application/rag/chunking_service.py`
- Create: `backend/app/application/rag/citation_service.py`
- Create: `backend/app/application/rag/retrieval_service.py`
- Create: `backend/app/application/rag/document_ingestion_service.py`
- Create: `backend/app/application/rag/rag_service.py`

- [x] **Step 1: Implement typed application models**

Add loaded-document, ingestion, retrieval, citation, and RAG response models.

- [x] **Step 2: Implement services**

Add recursive character chunking, document ingestion, retrieval, citations, prompt assembly, and grounded LLM answer generation.

### Task 3: Infrastructure Loaders And Embeddings

**Files:**
- Create: `backend/app/infrastructure/document_loaders/__init__.py`
- Create: `backend/app/infrastructure/document_loaders/pdf_loader.py`
- Create: `backend/app/infrastructure/document_loaders/docx_loader.py`
- Create: `backend/app/infrastructure/document_loaders/txt_loader.py`
- Create: `backend/app/infrastructure/document_loaders/markdown_loader.py`
- Create: `backend/app/infrastructure/document_loaders/factory.py`
- Create: `backend/app/infrastructure/embeddings/__init__.py`
- Create: `backend/app/infrastructure/embeddings/embedding_provider.py`
- Create: `backend/app/infrastructure/embeddings/bge_m3_provider.py`
- Create: `backend/app/infrastructure/embeddings/models.py`
- Modify: `backend/requirements.txt`

- [x] **Step 1: Implement file loaders**

Support PDF, DOCX, TXT, and Markdown through a loader factory.

- [x] **Step 2: Implement embedding abstraction**

Expose an embedding protocol and typed embedding result models; provide a local deterministic BGE-M3-compatible adapter that can later be replaced by a true model implementation.

### Task 4: Verification

- [x] **Step 1: Run Module 4 tests**

Run: `.venv/bin/python -m pytest tests/rag -v`

Expected: PASS.

- [x] **Step 2: Run full test suite**

Run: `.venv/bin/python -m pytest -v`

Expected: PASS.

### Self-Review

- Spec coverage: Covers supported file loaders, upload storage, cleaning, chunking, embedding abstraction, vector storage, retrieval filters and thresholds, citations, prompt rules, response model, token usage, and E2E flow.
- Placeholder scan: No TODO or TBD markers are present.
- Type consistency: RAG services use domain ports and typed application/infrastructure models consistently.
