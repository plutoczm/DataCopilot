# 部署指南

## 环境要求

- Python 3.12；
- 本地推荐 Conda；
- Docker Engine 24+ / Docker Compose v2；
- 推荐 Linux：Ubuntu 22.04+；
- 默认端口：backend `8000`、frontend `8501`、ChromaDB `8001`、Ollama `11434`。

## 本地启动

```bash
conda env create -f environment.yml
conda activate datacopilot
cp .env.example .env
python manage.py start --no-open
```

Windows 可使用：

```bat
start.cmd
```

默认：

- Streamlit：`http://127.0.0.1:8502`
- FastAPI：`http://127.0.0.1:8000/docs`

停止：

```bash
python manage.py stop
```

## 模型 Provider

运行时只选择一个主 Provider：`deepseek`、`openai` 或 `ollama`。模型选择发生在后端组合根，不存在任务级 local/cloud Routing Provider。

### DeepSeek

```text
DATACOPILOT_LLM__DEFAULT_PROVIDER=deepseek
DEEPSEEK_API_KEY=...
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
```

### OpenAI

```text
DATACOPILOT_LLM__DEFAULT_PROVIDER=openai
DATACOPILOT_OPENAI__ENABLED=true
DATACOPILOT_OPENAI__API_KEY=...
DATACOPILOT_OPENAI__BASE_URL=https://api.openai.com/v1
DATACOPILOT_OPENAI__CHAT_MODEL=gpt-4.1-mini
```

### Ollama

```bash
docker compose --profile ollama up -d ollama
docker compose exec ollama ollama pull qwen3
```

```text
LLM_PROVIDER=ollama
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen3
```

不要配置已经删除的 `ROUTING_ENABLED`、`LOCAL_MODEL_ENABLED`、`DATACOPILOT_LOCAL__*` 等变量。

## Docker 部署

1. 编辑 `docker/.env.production`，真实密钥只放环境或 Secret Store；
2. 校验：

```bash
docker compose --env-file docker/.env.production config --quiet
```

3. 启动：

```bash
docker compose --env-file docker/.env.production up -d --build
```

4. 查看：

```bash
docker compose ps
docker compose logs -f backend frontend chromadb
```

5. 停止：

```bash
docker compose down
```

`data/` 使用项目内 bind mount，`docker compose down` 不应删除这些宿主数据。

## 只读查询执行：默认关闭

生产默认值：

```text
DATACOPILOT_QUERY_EXECUTION__ENABLED=false
DATACOPILOT_QUERY_EXECUTION__DATASOURCE_NAME=retail_demo
DATACOPILOT_QUERY_EXECUTION__SQLITE_PATH=data/demo/retail_analytics.db
DATACOPILOT_QUERY_EXECUTION__MAX_ROWS=200
DATACOPILOT_QUERY_EXECUTION__TIMEOUT_MS=3000
```

SQLite 适配器用于**本地可复现演示**，不是生产数仓连接方案。

本地演示：

```bash
python examples/retail_analytics/setup_demo_db.py --force
```

然后仅在本地 `.env` 显式开启：

```text
DATACOPILOT_QUERY_EXECUTION__ENABLED=true
```

再启动应用。执行路径会叠加：

- datasource whitelist；
- ReadOnlySQLPolicy；
- SQLite URI `mode=ro`；
- `PRAGMA query_only=ON`；
- query deadline；
- server max rows；
- query audit。

### 生产数据库接入要求

未来接 MySQL / ClickHouse 时，至少需要：

1. 每个环境独立只读账号；
2. Secret Manager / Vault / KMS，不把 DSN 写入仓库；
3. 数据源和 Schema 白名单；
4. statement/query timeout；
5. 最大返回行数和 payload size；
6. 并发限制 / 资源组 / 最大扫描量；
7. Query ID、调用者、数据源、SQL hash、耗时、结果规模审计；
8. 敏感表/字段授权与脱敏；
9. 必要时人工确认。

应用层 ReadOnlySQLPolicy 不能替代数据库权限。

## 零售 Demo 与 Benchmark

```bash
python examples/retail_analytics/setup_demo_db.py --force
python manage.py start --no-open
python examples/retail_analytics/run_demo.py
python examples/retail_analytics/evaluate_text2sql.py
```

报告默认写入：

```text
data/evaluation/retail_text2sql_report.json
```

报告包含生成、校验、执行、Schema 幻觉、P95 延迟、Token 和 Safety 指标。运行结果属于当前模型/配置/数据集，不提交一个静态“宣传准确率”替代真实 benchmark。

## 服务与资源限制

| 服务 | 默认端口 | 职责 | Compose 资源上限 |
| --- | --- | --- | --- |
| backend | 8000 | API / Agent / RAG / SQL / Query Execution | 4 CPU / 8 GB |
| frontend | 8501 | Streamlit | 1 CPU / 2 GB |
| chromadb | 8001 | 向量检索 | 2 CPU / 4 GB |
| ollama | 11434 | 可选本地 LLM | 4 CPU / 8 GB |

Compose `deploy.resources` 之外还配置 `cpus` / `mem_limit` 以适配常见 Compose 运行方式。

## 持久化目录

```text
data/chromadb/      向量数据
data/uploads/       上传文档
data/logs/          结构化日志
data/cache/         缓存
data/embeddings/    Embedding 相关缓存
data/ollama/        Ollama 模型数据
data/demo/          本地演示数据库（运行时生成）
data/evaluation/    Benchmark 报告（运行时生成）
models/             项目本地模型目录
```

Demo DB 和 benchmark report 属于可重建运行时数据，不应当作源代码提交。

## 健康检查

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8501/_stcore/health
curl http://127.0.0.1:8001/api/v1/heartbeat
```

执行能力状态可查看：

```bash
curl http://127.0.0.1:8000/api/v1/query-execution/datasources
```

这个接口只暴露非敏感 datasource name/type/availability，不暴露本地 path 或未来数据库凭据。

## 常见故障

### Query Execution 返回 503

- `query_execution_disabled`：默认安全行为，检查是否确实需要开启；
- `datasource_unavailable`：本地 demo DB 是否已经初始化；
- 不要为了消除 503 自动将 production 默认值改成 true。

### Query Execution 返回 400

`query_rejected` 表示后端只读策略拒绝 SQL。不要在前端绕过策略或改为直接数据库连接。

### LLM 调用失败

- 检查 Provider 选择和密钥；
- 检查 Base URL、429、网络和 timeout；
- Ollama 检查模型是否已经 pull。

### 知识库无结果

- 检查摄取是否成功、collection 是否一致；
- 检查 metadata filter；
- 对比 hybrid/vector retrieval；
- 不应简单把 score threshold 永久调低来掩盖召回问题。

## 生产安全清单

- API Gateway / Nginx / Cloud LB：TLS、认证、限流；
- Secret Manager：模型/数据库凭据；
- 上传文件：大小、MIME、病毒扫描、租户隔离；
- 数据库：只读角色、白名单、超时、资源限制、审计；
- 可观测：集中日志、metrics、trace、告警；
- 数据持久化：备份和恢复演练；
- 下一阶段需要补充 App-level Auth、RBAC、Workspace/Tenant isolation。
