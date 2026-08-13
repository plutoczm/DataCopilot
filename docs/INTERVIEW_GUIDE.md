# 项目面试讲解

## 30 秒介绍

DataPilot-AI 是面向企业数据分析场景的 AI Application Copilot。我把它从“RAG + Text2SQL Demo”收敛成一条可验证应用链路：**企业指标知识 RAG → 数据源 Schema 自动发现 → Text2SQL → 确定性 SQL 安全校验 → SQL Review → 显式受治理只读执行 → Golden Result Benchmark**。项目同时具备 FastAPI、Streamlit、API Key/RBAC、Docker Compose、结构化日志和 GitHub Actions 质量门禁。

## 业务价值

传统流程是：业务提需求 → 查指标口径 → 查 Schema → 写 SQL → 审核 → 执行 → 验证。项目自动化其中规则清晰、可治理的部分：

- RAG 统一指标口径和数据规范；
- `SchemaCatalog` 自动读取已配置数据源元数据，避免人工复制 DDL；
- Text2SQL 生成候选 SQL；
- SQLValidator / SQL Review 降低 Schema 幻觉和运行风险；
- Query Execution 对白名单数据源提供显式只读执行；
- Golden SQL Oracle 比较真实查询结果，区分“能执行”和“答案正确”。

## 核心架构取舍

### 为什么采用端口/适配器？

应用层只依赖 `LLMProvider`、`VectorStore`、`QueryExecutor`、`SchemaCatalog`。DeepSeek/OpenAI/Ollama、ChromaDB、SQLite 都在基础设施层。这样可以用 Fake 实现做稳定测试，也能在不重写 Text2SQL 用例的情况下增加 MySQL/ClickHouse Catalog 与只读执行器。

### 为什么 QueryExecutor 和 SchemaCatalog 要拆开？

两者权限语义不同。读取表名/字段属于元数据访问；执行模型生成 SQL 会消耗数据库资源并读取真实业务数据。当前即使 `QUERY_EXECUTION__ENABLED=false`，仍可读取已配置数据源的非敏感 Schema 生成和审核 SQL。这体现了最小权限，而不是为了代码复用把两个能力绑在一起。

### 为什么 Schema 要有 fingerprint？

Text2SQL 结果必须知道自己基于哪一版元数据生成。SQLite Catalog 对稳定排序后的 DDL 做 SHA-256，返回 `schema_fingerprint`。它首先是 provenance，同时已经参与执行安全：Datasource 模式生成 SQL 后，UI 和 benchmark 会把该 fingerprint 作为执行前置条件回传，执行服务重新读取当前 Schema；如果 fingerprint 已变化，则返回 `409 schema_drift`，要求重新生成和审核 SQL，避免基于旧 Schema 的查询在新结构上盲跑。

### 为什么删除任务级多模型路由？

没有 benchmark 证明收益时，按 RAG/Text2SQL 分配不同模型会增加配置、故障路径和测试面。当前将模型选择收敛到组合根。未来如果质量/成本数据证明某模型在某任务显著更优，再引入路由。

### 为什么删除微调训练子系统？

目标是 AI Application Engineering。企业指标、Schema、规范经常变化，这类知识优先 RAG/Catalog；LoRA/SFT 属于 Model Engineering，放在独立项目更容易讲清训练数据、基线、评测和部署，而不是稀释应用主线。

### 为什么使用 LangGraph，但不堆 Multi-Agent？

LangGraph 用于显式状态和多步骤流程，比如 Text2SQL → Review。节点、路由、状态和终止条件可测试。当前没有业务证据需要多个自治 Agent，因此不增加额外通信、循环和故障复杂度。

### 为什么不让 Agent 自动执行 SQL？

即使只读查询也会占用数据库资源，并可能暴露敏感数据。执行器**不注册为 Agent Tool**：用户必须显式点击 UI 或调用 API，后端再做独立授权和安全检查。这比让 Agent 自主决定“什么时候查库”更可审计。

## 查询执行如何做防御纵深？

当前 SQLite 是可复现演示适配器，不包装成生产数据库方案。执行路径包含：

1. feature flag 默认关闭；
2. 仅允许配置 datasource；
3. API role 至少 analyst；
4. Datasource Text2SQL 可携带生成时 Schema fingerprint，执行前检查 Schema drift；
5. `ReadOnlySQLPolicy` 二次检查；
6. 只接受单条 `SELECT/WITH`；
7. 拒绝 DML/DDL/权限/管理语句、PRAGMA、extension/file loading；
8. SQLite URI `mode=ro`；
9. `PRAGMA query_only=ON`；
10. progress handler 实现 deadline；
11. 服务端最大返回行数；
12. Query ID + actor + SQL SHA-256 + 状态/耗时/行数审计。

应用层规则不能替代数据库权限。真正接 MySQL/ClickHouse 仍需要原生只读账号、Secret Manager、statement timeout、资源组/扫描量和并发限制。

## 高频技术问题

### 1. Text2SQL 如何降低幻觉？

Datasource 模式只使用 `SchemaCatalog` 返回的 Schema；Manual 模式只使用显式 Schema。模型输出后，SQLValidator 检查未知表/字段、JOIN、笛卡尔积、只读语句和引擎规则。执行阶段还有独立 ReadOnlySQLPolicy，避免生成阶段校验成为最终授权。

### 2. datasource 和 schema_context 为什么不能同时传？

因为它们可能描述两个不同版本甚至两个不同数据库。如果同时允许，系统无法清晰定义谁是 authoritative source。当前 API 要求二选一，并在 datasource 模式把 Schema fingerprint 放入结果 metadata。

### 3. 为什么 SQLValidator 和 Query Execution Policy 要两套？

职责不同：Validator 面向“生成质量”，包含 Schema、JOIN 和引擎规则；Execution Policy 面向“运行授权”，必须独立、最小、保守。未来来自人工或其他系统的 SQL 也不能绕过执行边界。

### 4. 为什么还需要 SQL Review？

Validator 负责确定性结构/安全规则；Review 负责更高层可读性、风险评分、性能建议和解释。安全核心不能完全依赖 LLM，但规则引擎也不适合承担所有业务语义判断。

### 5. RAG 如何降低幻觉？

Dense + BM25 混合召回、RRF 融合、轻量重排；Top K 上下文；引用返回；低分拒答。业务指标口径放进 RAG，而表结构优先来自 SchemaCatalog，避免把两种知识源混成一个大 Prompt。

### 6. 如何管理上下文和记忆？

单次流程用 `AgentState`；同 `session_id` 保存短期消息；超窗口历史做摘要。当前 Agent session 仍是进程内状态，生产版本应迁移 Redis/数据库并增加 workspace/tenant 隔离。文档 Registry 已经使用 SQLite 持久化。

### 7. 如何控制成本和延迟？

Embedding 在摄取阶段完成；RAG 裁剪上下文；Schema 直接从 Catalog 获取而不是让 LLM猜测；安全规则不调用 LLM；Provider 设置 timeout/retry；Benchmark 记录 generation P95 和 Token；查询执行有独立 deadline 和 row cap。优化由数据驱动，而不是先加缓存或多模型路由。

### 8. 现在如何评测 Text2SQL？

指标分层：

- Generation Success Rate；
- Valid SQL Rate；
- Execution Attempt / Success Rate；
- Expected Table Recall；
- Schema Hallucination Rate；
- Result Oracle Coverage；
- Result Comparison Rate；
- **Business Result Accuracy**；
- P95 Generation Latency；
- Execution Latency；
- Token Usage；
- Safety Policy Decision Accuracy；
- Unsafe Rejection / Safe Acceptance Rate。

### 9. Execution Success 和 Business Result Accuracy 有什么区别？

Execution Success 只说明 SQL 在数据库里没有报错。例如把 `SUM` 写成 `COUNT` 仍可能成功执行，但业务答案完全错误。

零售 benchmark 为每题提供 `golden_sql`。生成 SQL 与 Golden SQL 在同一个受治理数据源、同一个 Schema fingerprint precondition 下执行，然后比较结果集。`business_result_accuracy` 的分母是全部有 Oracle 的 case，所以生成失败、校验失败、执行失败都不会被从指标里排除。

当前 Oracle 适合小型聚合：忽略结果行顺序、列别名，并做有限数值精度归一化。复杂查询需要 case-specific oracle，不能宣称存在万能 SQL 等价判断。

### 10. 为什么 SQLite 有实际意义？

不是为了证明 SQLite 是生产数仓，而是让招聘者和 CI 能低成本复现“Schema discovery → SQL generation → validation → execution → result oracle → safety rejection”完整链路。生产数据源是新的 infrastructure adapter，不需要重写应用服务。

### 11. API 鉴权做到什么程度？

当前所有 `/api/v1/*` 位于受保护 Router 下，可选 `X-API-Key` 鉴权，角色包括 reader、analyst、admin；执行 SQL 至少 analyst，Schema 元数据 reader 即可。密钥采用 constant-time compare。

这只是轻量 RBAC，不伪装成完整 IAM。企业生产还需要 OIDC/SSO、workspace/tenant identity、租户级数据源授权和 Secret Manager。

### 12. 当前距离更成熟生产系统还差什么？

优先级是：

- 多数据源 Registry + MySQL/ClickHouse Catalog/Query adapters；
- OIDC/SSO + Workspace/Tenant 隔离；
- OpenTelemetry / LLM + Query tracing / metrics dashboard；
- 异步文档摄取任务；
- Redis/DB 分布式 session state；
- 版本化 benchmark、更多 case-specific oracle 和模型质量回归阈值。

这些是明确的边界，不写成已完成能力。

## Demo 顺序

1. Swagger：展示 `/auth/me`、OpenAPI Schema 和统一错误；
2. 上传 `metric_definitions.md`，展示业务口径 RAG；
3. 初始化 `retail_analytics.db`，但保持 execution 默认关闭；
4. 打开 Text2SQL 页面选择 `retail_demo`，展示自动 Schema、engine 和 fingerprint；
5. 输入“统计最近30天各区域GMV”，展示 SQL 与静态校验；
6. 显式开启只读执行，展示结果、Query ID、row cap；
7. 修改演示 Schema 后尝试执行旧 SQL，展示 `409 schema_drift`；
8. 提交 `DROP/DELETE/多语句/PRAGMA`，展示 Safety Policy 拒绝；
9. 运行 `evaluate_text2sql.py`，解释 Execution Success 和 Business Result Accuracy 的差别；
10. 展示 Docker Compose 和 GitHub Actions quality gate。

## 简历表达建议

不要只写：

> 使用 LangChain、LangGraph、RAG、ChromaDB 构建智能数据助手。

更有区分度的表达：

> 面向企业数据分析构建 AI Copilot，设计 `SchemaCatalog` 自动发现白名单数据源元数据并记录 Schema fingerprint，将指标知识 RAG、Text2SQL、确定性 SQL 校验与审核组织为可测试工作流；通过独立 `QueryExecutor`、RBAC、Schema drift precondition、数据库只读模式、deadline、row cap 与审计治理模型 SQL，并建立 Golden SQL result oracle 分离评估 SQL 有效率、执行成功率、Schema 幻觉、业务结果准确率、P95 延迟和 Token 成本。
