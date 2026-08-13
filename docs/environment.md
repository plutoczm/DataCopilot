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

## ChromaDB 说明

当前应用的 `ChromaDBVectorStore` 使用 `chromadb.PersistentClient(path=...)`，数据持久化在项目内 `data/chromadb/`。

`docker-compose.yml` 目前仍保留独立 ChromaDB Server 服务及 backend health dependency；它属于待收敛的历史部署拓扑，不应理解为当前 embedded vector-store 调用链的必需远程服务。后续应在删除该冗余服务或切换为真正的 HTTP client 两种方案中选择一种，避免同时维护两套拓扑。

## Legacy static web

仓库仍包含 `vercel.json`、`package.json`、`web/` 与 `scripts/build_web.py` 的历史浏览器模拟 Demo。它不属于当前 FastAPI + Streamlit 主应用链路，也不作为简历项目的生产运行入口；后续计划整体拆除。

因此，日常开发和主应用部署**不需要 Node.js 或 Vercel**。

## 项目内运行数据

缓存、日志、临时文件和持久化数据统一放在项目内的 `.runtime/`、`data/` 或 `models/` 目录，避免依赖用户机器的绝对路径。
