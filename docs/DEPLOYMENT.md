# 部署指南

## 环境要求

- 本地开发：Python 3.11+、Conda。
- Docker 部署：Docker Engine 24+、Docker Compose v2。
- 推荐生产系统：Ubuntu 22.04 或更新版本。
- 默认端口：后端 `8000`、前端 `8501`、ChromaDB `8001`、Ollama `11434`。

## 本地启动

在 Windows 上：

```bat
start.cmd
```

跨平台：

```bash
conda env create -f environment.yml
conda activate datacopilot
python manage.py start --no-open
```

默认本地工作台使用 `http://127.0.0.1:8502`，API 文档使用 `http://127.0.0.1:8000/docs`。

停止服务：

```bash
python manage.py stop
```

## Docker 部署

1. 准备生产环境变量：

```bash
cp docker/.env.production.example docker/.env.production
```

如果仓库没有示例文件，可直接编辑现有 `docker/.env.production`。至少配置 `DEEPSEEK_API_KEY`，且不要将真实密钥提交到 Git。

2. 校验配置：

```bash
docker compose --env-file docker/.env.production config --quiet
```

3. 构建并启动：

```bash
docker compose --env-file docker/.env.production up -d --build
```

4. 查看状态和日志：

```bash
docker compose ps
docker compose logs -f backend frontend chromadb
```

5. 停止服务：

```bash
docker compose down
```

`down` 不会删除绑定到项目 `data/` 目录的数据。不要使用 `down -v` 删除仍需保留的数据卷。

## 使用 Ollama 本地模型

```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull qwen3
```

设置以下变量后启动完整服务：

```text
LLM_PROVIDER=ollama
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen3
```

```bash
docker compose --profile ollama up -d
```

Ollama 健康检查不仅验证服务可达，还会验证目标模型是否已经拉取。

### 多 LLM 智能路由（专业任务 → 本地微调模型）

在本地完成 LoRA 微调并导出 GGUF 后（见 `training/README.md`），将模型导入 Ollama：

```bash
ollama create datacopilot-qwen3-8b -f training/export/Modelfile
```

开启智能路由，让 Text2SQL、SQL 审核、数仓设计等专业数据工程任务走本地微调模型，通用对话继续走云端：

```text
ROUTING_ENABLED=true
CLOUD_PROVIDER=deepseek
LOCAL_MODEL_ENABLED=true
LOCAL_MODEL_BASE_URL=http://ollama:11434/v1
LOCAL_MODEL_NAME=datacopilot-qwen3-8b
```

本地模型未导入或 Ollama 不可用时，专业任务自动降级到云端，不会中断服务。关闭 `ROUTING_ENABLED` 即回退为单一 provider 模式。本地开发环境对应的环境变量前缀为 `DATACOPILOT_LLM__ROUTING_*` 与 `DATACOPILOT_LOCAL__*`。

## 服务与资源限制

| 服务 | 默认端口 | 主要职责 | 默认资源上限 |
| --- | --- | --- | --- |
| `backend` | 8000 | FastAPI、Agent、RAG、SQL、数仓 | 4 CPU / 8 GB |
| `frontend` | 8501 | Streamlit 工作台 | 1 CPU / 2 GB |
| `chromadb` | 8001 | 向量持久化和检索 | 2 CPU / 4 GB |
| `ollama` | 11434 | 可选本地模型推理 | 4 CPU / 8 GB |

本地大模型实际内存需求取决于模型规模和量化方式，应根据机器资源调整 Compose 限制。

## 持久化目录

```text
data/chromadb/     ChromaDB 数据
data/uploads/      已摄取文档
data/logs/         后端和前端日志
data/cache/        缓存
data/embeddings/   Embedding 缓存
data/ollama/       Ollama 模型
models/            项目本地模型
```

生产环境需要定期备份 `data/chromadb`、`data/uploads` 和业务需要的模型目录，并验证恢复流程。

## 健康检查

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8501/_stcore/health
curl http://127.0.0.1:8001/api/v1/heartbeat
```

后端 `status=degraded` 时查看响应中的 `llm_provider` 和 `vector_store`。默认知识库集合会在首次访问时幂等创建。

## 常见故障

### 端口已占用

在 `.env.production` 中调整：

```text
BACKEND_PORT=18000
FRONTEND_PORT=18501
CHROMADB_PORT=18001
OLLAMA_PORT=11434
```

### Docker 目录权限不足

确保容器 UID/GID 对 `data/` 目录具备读写权限。不要通过给整个项目设置无限制权限来规避问题。

### 大模型调用失败

- DeepSeek：检查密钥、代理、Base URL、429 限流和超时。
- Ollama：检查服务、模型是否拉取，以及后端是否使用容器内地址 `http://ollama:11434`。
- 查看 `data/logs/backend.log` 中的 request ID 和异常类型。

### 知识库无结果

- 确认文档摄取成功且集合名一致。
- 检查元数据过滤条件。
- 暂时降低 `score_threshold` 比较结果。
- 使用 `retrieval_mode=hybrid` 改善关键词召回。

## 生产安全

- 使用 Nginx、Traefik 或云网关配置 TLS、认证和限流。
- 密钥使用 Secret Manager 或容器 Secret，不写入镜像和仓库。
- 为上传文件设置大小、类型、病毒扫描和租户隔离。
- SQL 执行必须使用只读账户、超时、行数限制和人工确认。
- 配置集中日志、指标、调用链和告警。
