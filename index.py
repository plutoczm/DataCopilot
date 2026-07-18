"""Vercel entrypoint for the DataPilot-AI FastAPI application.

本机和 Docker 始终使用项目根目录下的 ``data/``。只有 Vercel 云函数需要
使用临时目录：Vercel 部署包是只读的，云端实例也不提供长期磁盘，因此把
临时 ChromaDB、上传、缓存和日志放在云函数自己的 ``/tmp`` 中。该路径不
会映射到用户电脑，也不会在本机创建 C 盘目录。环境变量必须在导入应用
之前设置，因为应用会在模块导入时构造配置。
"""

from __future__ import annotations

import os
from pathlib import Path


def _configure_vercel_runtime() -> None:
    data_root = Path("/tmp/datacopilot-data")
    os.environ.setdefault("DATACOPILOT_WEB_CONSOLE", "true")
    os.environ.setdefault("DATACOPILOT_ENVIRONMENT", "production")
    os.environ.setdefault("DATACOPILOT_DEBUG", "false")
    os.environ.setdefault("DATACOPILOT_RUNTIME__API_ONLY", "true")
    os.environ.setdefault("DATACOPILOT_PATHS__PROJECT_ROOT", "/tmp")
    os.environ.setdefault("DATACOPILOT_PATHS__DATA_DIR", str(data_root))
    os.environ.setdefault("DATACOPILOT_PATHS__CHROMADB_DIR", str(data_root / "chromadb"))
    os.environ.setdefault("DATACOPILOT_PATHS__UPLOADS_DIR", str(data_root / "uploads"))
    os.environ.setdefault("DATACOPILOT_PATHS__LOGS_DIR", str(data_root / "logs"))
    os.environ.setdefault("DATACOPILOT_PATHS__CACHE_DIR", str(data_root / "cache"))
    os.environ.setdefault("DATACOPILOT_PATHS__EMBEDDINGS_DIR", str(data_root / "embeddings"))
    os.environ.setdefault("DATACOPILOT_PATHS__TEMP_DIR", str(data_root / "temp"))
    os.environ.setdefault("DATACOPILOT_PATHS__MODELS_DIR", "/tmp/datacopilot-models")
    os.environ.setdefault("DATACOPILOT_LOGGING__FILE_ENABLED", "false")
    os.environ.setdefault("DATACOPILOT_APP__CORS_ORIGINS", '["*"]')


_configure_vercel_runtime()

from backend.app.main import app  # noqa: E402


# This module is the Vercel-only entrypoint.  The API keeps ``/`` as a JSON
# metadata endpoint in Docker; here we serve the browser console from the same
# origin while preserving every existing API route under ``/health`` and
# ``/api/v1/*``.
