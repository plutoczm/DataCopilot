# DeepSeek Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a swappable async LLM provider interface and DeepSeek provider implementation with structured responses, streaming, retries, timeout handling, health checks, and tests.

**Architecture:** Business code depends on `backend/app/domain/ports/llm_provider.py` only. DeepSeek-specific HTTP details live under `backend/app/infrastructure/llm`, making OpenAI, Ollama, and local LLM providers replaceable without changing application/domain code.

**Tech Stack:** Python 3.12, `typing.Protocol`, pydantic models, httpx async client, pytest.

---

### Task 1: Provider Contract Tests

**Files:**
- Create: `tests/infrastructure/test_deepseek_provider.py`

- [x] **Step 1: Write failing tests**

Cover chat success, streaming success, missing API key health status, model health check, auth failure, rate limit failure, timeout mapping, connection retry behavior, response validation, token counting, and provider name.

- [x] **Step 2: Run tests to verify failure**

Run: `.venv/bin/python -m pytest tests/infrastructure/test_deepseek_provider.py -v`

Expected: FAIL until dependencies and provider files exist.

### Task 2: Domain Port And Infrastructure Models

**Files:**
- Create: `backend/app/domain/ports/llm_provider.py`
- Create: `backend/app/domain/ports/__init__.py`
- Create: `backend/app/infrastructure/llm/models.py`
- Create: `backend/app/infrastructure/llm/exceptions.py`
- Create: `backend/app/infrastructure/llm/__init__.py`

- [x] **Step 1: Define provider protocol**

Expose `chat`, `stream_chat`, `health_check`, `token_count`, and `provider_name`.

- [x] **Step 2: Define typed models and exceptions**

Add request/response/message/usage/health models and custom LLM exceptions.

### Task 3: DeepSeek Provider

**Files:**
- Create: `backend/app/infrastructure/llm/deepseek_provider.py`
- Modify: `backend/requirements.txt`
- Modify: `.env.example`

- [x] **Step 1: Add httpx dependency**

Add `httpx` and refresh the project-local `.venv` with `scripts/bootstrap_venv.sh`.

- [x] **Step 2: Implement provider**

Implement async chat, SSE streaming, health check, retry with exponential backoff, timeout/read timeout, response validation, usage statistics, token tracking, and HTTP error mapping.

### Task 4: Verification

**Files:**
- Test: `tests/infrastructure/test_deepseek_provider.py`
- Test: full suite

- [x] **Step 1: Run Module 6 tests**

Run: `.venv/bin/python -m pytest tests/infrastructure/test_deepseek_provider.py -v`

Expected: PASS.

- [x] **Step 2: Run full test suite**

Run: `.venv/bin/python -m pytest -v`

Expected: PASS.

### Self-Review

- Spec coverage: Covers Clean Architecture port, DeepSeek swappable implementation, async HTTP, streaming, timeouts, retries, structured errors, response validation, usage, token tracking, settings integration, and tests.
- Placeholder scan: No TODO or TBD markers are present.
- Type consistency: Tests import the exact public models and provider methods implemented by the module.
