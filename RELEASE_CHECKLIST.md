# Release Checklist

Use this checklist before publishing DataPilot-AI to GitHub or presenting it in an interview.

## Repository

- [ ] README uses the DataPilot-AI project name.
- [ ] MIT license is present.
- [ ] CONTRIBUTING guide is present.
- [ ] GitHub Actions workflow is present.
- [ ] No secrets are committed.
- [ ] `.env` is not committed.
- [ ] Runtime data directories contain only `.gitkeep` files.
- [ ] `vercel.json`, root `index.py`, and `public/index.html` are present.
- [ ] Windows one-click startup (`start.ps1` / `start.bat`) works.

## Docker Compose

- [ ] `docker compose --env-file docker/.env.production config` passes.
- [ ] `docker compose --env-file docker/.env.production up -d` starts services.
- [ ] `docker compose --env-file docker/.env.production ps` shows expected containers.
- [ ] No anonymous volumes are created.
- [ ] Data persists under `./data`.
- [ ] Resource limits match backend 4 CPU/8G, frontend 1 CPU/2G, ChromaDB 2 CPU/4G.

## Vercel

- [ ] `vercel.cmd deploy --prod` succeeds.
- [ ] `/` opens the public web console from a second network.
- [ ] `/health`, `/docs`, and `/openapi.json` return successfully.
- [ ] `DEEPSEEK_API_KEY` is configured as a Vercel production environment variable, never committed.
- [ ] Persistent ChromaDB is externalized before production use.

## Backend

- [ ] `GET /` returns service metadata.
- [ ] `GET /health` returns structured health.
- [ ] `GET /docs` opens Swagger UI.
- [ ] `GET /openapi.json` returns schema.
- [ ] Logs are written under `data/logs`.

## Frontend

- [ ] Streamlit starts on port 8501 or configured override.
- [ ] Sidebar shows backend health.
- [ ] Agent Chat streams responses.
- [ ] Knowledge Base upload/list/query works.
- [ ] Text2SQL, SQL Review, and Warehouse Designer pages render.

## Agent

- [ ] RAG intent works.
- [ ] Text2SQL intent works.
- [ ] SQL Review intent works.
- [ ] Warehouse Design intent works.
- [ ] General Chat intent works.
- [ ] Multi-step Text2SQL plus SQL Review works.

## RAG

- [ ] TXT upload works.
- [ ] Markdown upload works.
- [ ] Retrieval returns citations.
- [ ] RAG answer includes source metadata.

## Tests

- [ ] Unit tests pass.
- [ ] API tests pass.
- [ ] Infrastructure tests pass.
- [ ] Integration tests pass.
- [ ] Deployment tests pass.

## Coverage

- [ ] Coverage command passes:

```bash
.venv/bin/python -m pytest --cov=backend --cov=frontend --cov-report=term-missing --cov-fail-under=85
```

- [ ] Coverage is at least 85%.

## Demo

- [ ] Prepare screenshots under `docs/assets/`.
- [ ] Prepare demo prompts:
  - `什么是Spark AQE`
  - `统计最近7天活跃用户并检查SQL`
  - `设计电商订单分析数仓`
- [ ] Prepare one uploaded technical document.
- [ ] Prepare resume bullet and project story.
