# Project Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the DataPilot-AI repository skeleton under `/mnt/ext-disk/czm2025/Projects/DataCopilot` with stable backend, frontend, data, deployment, test, and documentation boundaries.

**Architecture:** This module creates only structural contracts. Business code, configuration loading, logging, RAG, providers, APIs, UI pages, Docker runtime, and documentation content are implemented in later approved modules.

**Tech Stack:** Python 3.12 project layout, FastAPI-ready backend package structure, Streamlit-ready frontend package structure, pytest contract tests.

---

### Task 1: Project Root Contract

**Files:**
- Create: `tests/test_project_skeleton.py`
- Create: `.gitignore`
- Create: `README.md`
- Create directories listed in the approved architecture.

- [x] **Step 1: Write the failing test**

```python
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_required_top_level_directories_exist() -> None:
    required_directories = [
        "backend",
        "frontend",
        "knowledge_base",
        "data/chromadb",
        "data/uploads",
        "data/logs",
        "data/cache",
        "data/embeddings",
        "data/temp",
        "docker",
        "docs",
        "tests",
        "scripts",
        "models",
    ]

    missing = [
        directory
        for directory in required_directories
        if not (PROJECT_ROOT / directory).is_dir()
    ]

    assert missing == []
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_project_skeleton.py -v`

Expected: FAIL with missing skeleton directories.

- [x] **Step 3: Write minimal implementation**

Create the approved directories and lightweight marker files so empty runtime directories are preserved by git.

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_project_skeleton.py -v`

Expected: PASS.

### Task 2: Python Package Boundaries

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/presentation/__init__.py`
- Create: `backend/app/presentation/api/__init__.py`
- Create: `backend/app/application/__init__.py`
- Create: `backend/app/domain/__init__.py`
- Create: `backend/app/infrastructure/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `frontend/app.py`
- Create: `frontend/pages/.gitkeep`
- Create: `frontend/components/.gitkeep`
- Create: `frontend/services/.gitkeep`

- [x] **Step 1: Extend the skeleton test**

Add assertions for backend and frontend package entrypoints.

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_project_skeleton.py -v`

Expected: FAIL with missing package files.

- [x] **Step 3: Create package files**

Create importable packages and minimal entrypoints without business behavior.

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_project_skeleton.py -v`

Expected: PASS.

### Task 3: Storage Boundary Contract

**Files:**
- Modify: `tests/test_project_skeleton.py`

- [x] **Step 1: Add runtime storage path assertions**

Assert all required persistent runtime directories are descendants of the project root.

- [x] **Step 2: Run test to verify it passes**

Run: `pytest tests/test_project_skeleton.py -v`

Expected: PASS.

### Self-Review

- Spec coverage: Module 1 covers root structure, backend/frontend package boundaries, runtime data directories, scripts/docs/docker placeholders, and no business implementation.
- Placeholder scan: No TODO or TBD markers are present.
- Type consistency: The only executable contract is a pytest module using `pathlib.Path`.
