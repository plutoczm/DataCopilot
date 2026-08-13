# 运行环境

## 主应用运行时

- Python：**3.12**。本地 Conda、GitHub Actions、backend/frontend Docker image 统一使用同一 minor version。
- 推荐本地环境：Conda，环境名 `datacopilot`；也可以使用项目内 `.venv`。
- 主应用：FastAPI backend + Streamlit frontend，不依赖 Node.js。
- Docker：用于 backend、frontend 和可选 Ollama 的可复现部署。
- 操作系统：Windows、Linux 或 macOS；生产部署推荐 Linux。

Python 依赖分别维护在：

- `backend/requirements.txt`
- `frontend/requirements.txt`
- `requirements-dev.txt`

CI 会在安装后执行 `python -m pip check`，并运行 compile、Docker Compose config validation、pytest 与 coverage gate。

## ChromaDB

当前应用使用 `chromadb.PersistentClient`，持久化目录为项目内 `data/chromadb/`。Docker backend 将 `./data` 挂载到 `/app/data`，因此向量数据可以随项目数据目录持久化。

当前 Compose 是单 backend 实例拓扑，不再启动独立 ChromaDB 容器。部署结构与应用真实调用链保持一致，也避免为未使用的服务分配额外端口和资源。

## Legacy static web

仓库仍包含 `vercel.json`、`package.json`、`web/` 与 `scripts/build_web.py` 的历史浏览器模拟 Demo。它不属于当前 FastAPI + Streamlit 主应用链路，也不作为简历项目的生产运行入口；后续计划整体拆除。

因此，日常开发和主应用部署**不需要 Node.js 或 Vercel**。

## 项目内运行数据

缓存、日志、临时文件和持久化数据统一放在项目内的 `.runtime/`、`data/` 或 `models/` 目录，避免依赖用户机器的绝对路径。
