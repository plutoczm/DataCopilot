# Deployment

This guide deploys DataPilot-AI on Ubuntu 20.04 with Docker Compose.

## Vercel（公网 API + 轻量 Web 控制台）

Vercel 适合运行本项目的 FastAPI API 和 `public/index.html` 控制台。完整 Streamlit 多页面界面仍建议使用下方 Docker Compose 部署，因为 Streamlit 需要长驻进程和 WebSocket。

项目根目录已经包含 `index.py`、`vercel.json`、`requirements.txt` 和 `public/index.html`，可以直接部署：

```bash
npm i -g vercel
vercel login
vercel link
vercel env add DEEPSEEK_API_KEY production
vercel env add DEEPSEEK_BASE_URL production
vercel deploy --prod
```

部署完成后，打开 Vercel 输出的域名即可从其他网络访问控制台；API 文档在 `/docs`，健康检查在 `/health`。

本机和 Docker 的数据固定保存在项目根目录 `data/`。只有 Vercel 云函数因为部署包只读，代码才会把云端临时数据写入 `/tmp/datacopilot-data`；这不是你电脑的 C 盘路径，也不会改变本地目录。生产环境请把 ChromaDB、上传文件和日志迁移到外部持久化服务，并在 Vercel 项目环境变量中配置对应连接信息。

## Requirements

- Ubuntu 20.04
- Docker Engine 24+
- Docker Compose v2
- Run commands from the project root.
- Writable data directory: `./data`

## Production Setup

```bash
cp docker/.env.production docker/.env.local
```

Set secrets in your shell or local env file:

```bash
export DEEPSEEK_API_KEY=your_api_key
```

Validate configuration:

```bash
docker compose --env-file docker/.env.production config
```

Start services:

```bash
docker compose --env-file docker/.env.production up -d
```

Stop services:

```bash
docker compose --env-file docker/.env.production down
```

Restart services:

```bash
docker compose --env-file docker/.env.production restart
```

## Services

| Service | Port | Purpose |
| --- | ---: | --- |
| backend | 8000 | FastAPI backend |
| frontend | 8501 | Streamlit UI |
| chromadb | 8001 | ChromaDB service |
| ollama | 11434 | Optional local LLM profile |

Optional Ollama profile:

```bash
docker compose --env-file docker/.env.production --profile ollama up -d
```

## Resource Limits

| Service | CPU | RAM |
| --- | ---: | ---: |
| backend | 4 | 8G |
| frontend | 1 | 2G |
| chromadb | 2 | 4G |

## Persistence

All runtime data is stored under:

```text
./data
```

Important paths:

```text
data/chromadb      vector database persistence
data/uploads       uploaded documents
data/logs          application logs
data/cache         cache files
data/embeddings    embedding cache and generated vectors
data/temp          temporary files
data/models        local model files
data/ollama        optional Ollama model store
```

No anonymous Docker volumes are used.

## Health Checks

Backend:

```bash
curl http://localhost:8000/health
```

Frontend:

```bash
curl http://localhost:8501/_stcore/health
```

ChromaDB:

```bash
curl http://localhost:8001/api/v1/heartbeat
```

Inspect Compose health:

```bash
docker compose --env-file docker/.env.production ps
```

## Log Locations

Application log:

```text
data/logs/datacopilot.log
```

Docker service logs:

```bash
docker compose --env-file docker/.env.production logs -f backend
docker compose --env-file docker/.env.production logs -f frontend
docker compose --env-file docker/.env.production logs -f chromadb
```

## Troubleshooting

### Docker Permission Denied

If Docker reports permission denied on `/var/run/docker.sock`, add the user to the Docker group and re-login:

```bash
sudo usermod -aG docker "$USER"
newgrp docker
```

### Port Already In Use

Override ports:

```bash
FRONTEND_PORT=8502 docker compose --env-file docker/.env.production up -d
```

Supported overrides:

```text
BACKEND_PORT
FRONTEND_PORT
CHROMADB_PORT
OLLAMA_PORT
```

### Backend Health Is Degraded

Common causes:

- `DEEPSEEK_API_KEY` is missing.
- The default ChromaDB collection has not been created yet.
- External LLM API is unreachable.

The backend health endpoint still returns HTTP 200 with structured degraded status so orchestration can inspect the reason.

### Bind Mount Permission Issues

The backend and frontend containers run as non-root. Configure UID/GID in `docker/.env.production`:

```text
DATACOPILOT_UID=1014
DATACOPILOT_GID=1015
```

Make sure the data directory is writable by that UID/GID.

## Backup Strategy

Back up these directories:

```bash
tar -czf datapilot-ai-data-$(date +%F).tar.gz \
  data/chromadb data/uploads data/logs data/embeddings
```

Recommended cadence:

- Daily backup for `data/chromadb` and `data/uploads`.
- Weekly full backup for the full `data/` directory.
- Store at least one copy outside the host.

Restore:

```bash
docker compose --env-file docker/.env.production down
tar -xzf datapilot-ai-data-YYYY-MM-DD.tar.gz
docker compose --env-file docker/.env.production up -d
```
