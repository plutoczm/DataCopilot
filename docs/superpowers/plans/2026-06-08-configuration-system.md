# Configuration System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a strongly typed `pydantic-settings` configuration system for DataPilot-AI with environment separation, project-root path defaults, provider configuration, validation, and unit tests.

**Architecture:** Configuration lives in `backend/app/core` and exposes typed settings models plus cached loading helpers. Paths default to `/mnt/ext-disk/czm2025/Projects/DataCopilot` and are validated to stay under that root. Provider configuration is included for DeepSeek now and OpenAI/Ollama later without binding business logic to any provider.

**Tech Stack:** Python 3.12, pydantic v2, pydantic-settings, pytest.

---

### Task 1: Settings Contract Tests

**Files:**
- Create: `tests/core/test_settings.py`

- [x] **Step 1: Write failing tests**

Write tests for defaults, environment file precedence, project-local path validation, production safety validation, and cached settings helpers.

- [x] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/core/test_settings.py -v`

Expected: FAIL because `backend.app.core.settings` does not exist.

### Task 2: Core Settings Implementation

**Files:**
- Create: `backend/app/core/constants.py`
- Create: `backend/app/core/settings.py`
- Create: `backend/app/core/config.py`
- Create: `.env.example`
- Create: `backend/requirements.txt`
- Modify: `scripts/bootstrap_venv.sh`
- Modify: `README.md`

- [x] **Step 1: Add dependency metadata**

Add `pydantic` and `pydantic-settings` to `backend/requirements.txt`, and teach the bootstrap script to install them.

- [x] **Step 2: Implement constants**

Define canonical project paths, environment values, provider names, and default provider URLs/models.

- [x] **Step 3: Implement settings models**

Create typed settings models with `SettingsConfigDict`, `.env.example` and `.env` loading, nested env delimiter, enum validation, path validation, and production safety checks.

- [x] **Step 4: Implement config helpers**

Expose `get_settings`, `load_settings`, and `clear_settings_cache`.

- [x] **Step 5: Add environment example**

Create `.env.example` with all supported keys and project-local path defaults.

- [x] **Step 6: Update README**

Document how to bootstrap and use the settings system.

### Task 3: Verification

**Files:**
- Test: `tests/core/test_settings.py`
- Test: `tests/test_project_skeleton.py`

- [x] **Step 1: Run Module 2 tests**

Run: `.venv/bin/python -m pytest tests/core/test_settings.py -v`

Expected: PASS.

- [x] **Step 2: Run full test suite**

Run: `.venv/bin/python -m pytest -v`

Expected: PASS.

### Self-Review

- Spec coverage: Covers pydantic-settings, development/test/production enum, `.env.example` and `.env` loading, project-root path defaults, DeepSeek/OpenAI/Ollama sections, strong typing, validation, required generated files, unit tests, and README update.
- Placeholder scan: No TODO or TBD markers are present.
- Type consistency: Tests import the same public names implemented in `settings.py` and `config.py`.
