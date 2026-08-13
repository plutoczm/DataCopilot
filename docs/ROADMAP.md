# 项目路线图

路线图遵循一个原则：**只有真实业务链路、测试和评测能证明收益的能力，才进入主项目。** 未完成项不在 README 中包装成现有能力。

## 已完成

### AI 应用主链路

- FastAPI 后端、Streamlit 前端和 Ports & Adapters 风格分层；
- DeepSeek / OpenAI / Ollama 统一 `LLMProvider`；
- TXT、Markdown、PDF、DOCX 文档摄取；
- BGE-M3 + ChromaDB；
- Dense + BM25 混合召回、RRF、轻量重排、引用和低分拒答；
- SQLite 持久化文档 Registry；
- Text2SQL、SQL Review、数仓设计；
- LangGraph 意图路由、多步骤工作流、结果校验、短期记忆和 SSE；
- `SchemaCatalog` 端口与 SQLite Schema 自动发现；
- Schema fingerprint / provenance；
- datasource-driven Text2SQL，避免手工复制 DDL；
- 单条只读 SQL 静态校验与危险 DML/DDL/管理语句拒绝。

### 数据访问治理

- 独立 `QueryExecutor` / `QueryExecutionService`；
- SQL execution feature flag 默认关闭；
- datasource whitelist；
- `ReadOnlySQLPolicy`；
- SQLite `mode=ro` + `query_only`；
- query deadline、server row cap；
- Query ID / actor / SQL SHA-256 / latency 审计；
- API Key 鉴权；
- reader / analyst / admin 轻量 RBAC；
- Schema 元数据访问和 SQL execution 权限分离。

### Evaluation

- Agent intent / retrieval / tool-success 指标；
- Text2SQL generation / validation / execution 指标；
- expected table recall 与 schema hallucination；
- latency / token 指标；
- Safety Policy benchmark；
- 零售场景 `golden_sql` result oracle；
- `business_result_accuracy` 端到端业务结果准确率；
- 可复现 SQLite seed data 和 benchmark runner。

### 工程交付

- Docker Compose、健康检查、资源限制和项目内持久化；
- request ID / trace ID / JSON logging；
- Python compile gate；
- Docker Compose config gate；
- pytest + coverage >= 85% GitHub Actions 门禁；
- 明确区分开发默认值与 production safety validation。

## 近期优先级

### P0：多数据源 Registry

目标不是简单增加驱动数量，而是把“数据源配置、元数据、权限、执行器”变成可治理模型。

- 数据源 Registry：name、engine、metadata capabilities、execution capabilities、owner/status；
- MySQL SchemaCatalog + read-only QueryExecutor；
- ClickHouse SchemaCatalog + read-only QueryExecutor；
- 数据库凭据只从 Secret Manager / CI Secret / runtime secret 注入；
- datasource health / schema refresh；
- Schema fingerprint 变化检测；
- 数据源级 RBAC，为不同 workspace/tenant 限制可见数据源。

### P0：企业身份与租户隔离

当前 API-key RBAC 适合演示和内部服务，不是完整 IAM。

- OIDC / OAuth2 / SSO；
- Workspace / Tenant ID；
- tenant-scoped datasource、knowledge collection、session 和 audit；
- admin/analyst/reader 角色映射到外部身份；
- API key rotation / expiry / revocation；
- Secret Manager。

### P1：可观测性与 SLO

- OpenTelemetry trace/span；
- FastAPI request span；
- LLM provider latency/token/error span；
- RAG retrieval span；
- query execution span；
- P50/P95 latency、error rate、token cost、rejection rate dashboard；
- request ID / trace ID / query ID 关联；
- 评测指标与线上指标分开存储。

### P1：评测回归门禁

已有 Golden Result Oracle 后，下一步不是再写更多“准确率”字段，而是把评测变成发布流程的一部分。

- 固定 benchmark dataset version；
- 固定模型/provider/prompt configuration metadata；
- case-specific oracle；
- 更严格处理 row ordering、duplicate、NULL、timestamp、floating-point；
- 保存 baseline report；
- PR/Release 对比业务准确率、幻觉率、P95、Token；
- 明确 regression threshold，低于阈值阻断模型/Prompt 发布。

### P1：异步文档摄取

- background job / queue；
- ingestion job ID；
- processing / succeeded / failed 状态；
- 幂等 key；
- retry/backoff；
- dead-letter / failure inspection；
- 大文档分片与 progress。

### P2：分布式状态

- Agent session 从进程内迁移 Redis / database；
- 多实例共享状态；
- TTL 与容量治理；
- 用户/tenant 级数据隔离；
- cache invalidation 与 Schema fingerprint 联动。

### P2：RAG 质量升级

只有 benchmark 证明需要时再增加复杂组件：

- Cross-Encoder / LLM rerank；
- BGE-M3 native sparse retrieval；
- PGVector/Qdrant/Milvus adapter；
- versioned golden Q&A；
- faithfulness / citation correctness；
- metadata filtering recall benchmark。

## 暂不进入主项目

### 微调训练流水线

QLoRA / Unsloth / SFT 不再与 DataPilot-AI 主仓库耦合。若后续需要领域微调，应建立独立 Model Engineering 项目，并至少具备：数据版本、基线模型、训练配置、离线评测、部署成本和回滚策略。

### 任务级多模型智能路由

没有质量/成本 benchmark 前不增加 RAG/Text2SQL → 不同模型的复杂路由。只有真实数据证明收益超过故障和维护成本时再引入。

### Multi-Agent 堆叠

当前 LangGraph + Structured Tools 已能表达主要流程。除非出现明确的并行自治职责和可量化收益，否则不增加多 Agent 通信、循环和状态复杂度。

## 中长期探索

- Hive Metastore / Spark Catalog / Iceberg metadata；
- SQL lineage / impact analysis；
- ClickHouse explain / scan-cost guardrail；
- 人工审批与高风险操作 confirmation；
- Kafka/Flink 实时链路诊断；
- hosted demo / release image / SBOM / vulnerability scan。

规划内容不代表当前已实现能力，当前状态以 README、测试、benchmark 报告和发布记录为准。
