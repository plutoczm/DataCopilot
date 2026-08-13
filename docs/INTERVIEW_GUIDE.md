# 项目面试讲解

## 30 秒介绍

DataPilot-AI 是面向企业数据分析场景的 AI Application Copilot。我把它从“RAG + Text2SQL Demo”收敛成了一条可验证应用链路：**企业指标知识 RAG → Text2SQL → 确定性 SQL 安全校验 → SQL Review → 显式受治理只读执行 → benchmark**。项目同时有 FastAPI、Streamlit、Docker Compose、结构化日志和 GitHub Actions 质量门禁。

## 业务价值

传统流程是：业务提需求 → 查指标口径 → 查 Schema → 写 SQL → 审核 → 执行 → 验证。项目自动化其中规则清晰、可治理的部分：

- RAG 统一指标口径和数据规范；
- Text2SQL 生成候选 SQL；
- SQLValidator / SQL Review 降低幻觉和风险；
- Query Execution 对白名单数据源提供显式只读执行；
- Benchmark 记录生成、校验、执行、幻觉、延迟和 Token，而不是凭感觉说效果好。

## 核心架构取舍

### 为什么采用端口/适配器？

应用层只依赖 `LLMProvider`、`VectorStore`、`QueryExecutor`。DeepSeek/OpenAI/Ollama、ChromaDB、SQLite 都在基础设施层。这样可以用 Fake 实现做测试，也能在不修改 Text2SQL 业务逻辑的情况下增加 MySQL/ClickHouse 只读适配器。

### 为什么删除任务级多模型路由？

没有真实 benchmark 证明收益时，按 RAG/Text2SQL 分配不同模型会增加配置、故障路径和测试面。当前将模型选择收敛到组合根。未来如果质量/成本数据证明某模型在某任务显著更优，再引入路由。

### 为什么删除微调训练子系统？

目标是 AI Application Engineering。企业指标、Schema、规范经常变化，这类知识优先 RAG；LoRA/SFT 属于 Model Engineering，放在独立项目里更容易讲清楚训练数据、基线、评测和部署，而不是稀释应用主线。

### 为什么使用 LangGraph，但不做 Multi-Agent 堆叠？

LangGraph 用于显式状态和多步骤流程，比如 Text2SQL → Review。节点、路由、状态和终止条件可测试。当前没有业务证据需要多个自治 Agent，因此不增加额外通信、循环和故障复杂度。

### 为什么不让 Agent 自动执行 SQL？

即使只读查询也会消耗数据库资源，并可能暴露敏感数据。当前执行器已经实现，但它**不注册为 Agent Tool**：用户需要显式点击 UI 或调用 API，后端再做独立安全检查。这比让 Agent 自主决定“什么时候查库”更容易审计和控制。

## 查询执行是怎么做防御纵深的？

当前 SQLite 是可复现演示适配器，不包装成生产方案。执行路径包括：

1. feature flag 默认关闭；
2. 仅允许配置中的 datasource；
3. `ReadOnlySQLPolicy` 二次检查；
4. 只接受单条 `SELECT/WITH`；
5. 拒绝 DML/DDL/权限/管理语句、PRAGMA、extension/file loading；
6. SQLite URI `mode=ro`；
7. `PRAGMA query_only=ON`；
8. progress handler 实现 deadline；
9. 服务端最大返回行数；
10. Query ID + SQL SHA-256 + 状态/耗时/行数审计。

面试时要强调：应用层正则/Parser **不能替代数据库权限**。真正接 MySQL/ClickHouse 还需要只读账号、Secret Manager、statement timeout、资源组/扫描量和并发限制。

## 高频技术问题

### 1. Text2SQL 如何降低幻觉？

Prompt 只注入允许的 Schema 和可选 RAG 业务上下文；模型 JSON 输出后，SQLValidator 检查未知表/字段、JOIN、笛卡尔积、只读语句和引擎规则。执行阶段还有第二套 ReadOnlySQLPolicy，避免把生成阶段校验当成最终授权。

### 2. 为什么 SQLValidator 和 Query Execution Policy 要两套？

职责不同：Validator 面向“生成质量”，包含 Schema、JOIN、引擎建议；Execution Policy 面向“运行授权”，必须独立、最小、保守。这样未来 Text2SQL 之外的 SQL 来源也不能绕过执行边界。

### 3. 为什么还需要 SQL Review？

Validator 负责确定性结构/安全规则；Review 负责更高层可读性、风险评分、性能建议和解释。安全核心不能完全依赖 LLM，但规则引擎也不适合承担所有业务语义判断。

### 4. RAG 如何降低幻觉？

Dense + BM25 混合召回、RRF 融合、轻量重排；Top K 上下文；引用返回；低分拒答。后续需要 golden Q&A 和忠实度指标，而不是只看向量相似度。

### 5. 如何管理上下文和记忆？

单次流程用 `AgentState`；同 `session_id` 保存短期消息；超窗口历史做摘要。当前是进程内状态，生产版本应迁移 Redis/数据库，并增加 workspace/tenant 隔离。

### 6. 如何控制成本和延迟？

Embedding 在摄取阶段完成；RAG 裁剪上下文；安全规则不调用 LLM；Provider 设置 timeout/retry；Benchmark 记录 generation P95 和 Token；查询执行有独立 deadline 和 row cap。优化应由这些数据驱动，而不是先加缓存/多模型路由。

### 7. 现在如何评测 Text2SQL？

不使用一个笼统“准确率”：

- Generation Success Rate；
- Valid SQL Rate；
- Execution Success Rate；
- Expected Table Recall；
- Schema Hallucination Rate；
- P95 Generation Latency；
- Token Usage；
- Safety Policy Decision Accuracy；
- Unsafe Rejection Rate / Safe Acceptance Rate。

`Execution Success` **不等于业务结果正确率**。真正的业务 Accuracy 要增加 golden SQL/result oracle，比较查询结果语义。

### 8. 为什么 SQLite 有实际意义？

不是为了证明 SQLite 是生产数仓，而是让招聘者/CI 可以低成本复现“生成 SQL → 实际执行 → 返回数据 → 安全拒绝”的完整链路。生产数据源适配器是下一层 infrastructure adapter，而不是重写应用服务。

### 9. 为什么 ChromaDB？

单机演示部署成本低，适合验证 RAG 主链路。`VectorStore` 端口保留了迁移到 PGVector/Qdrant/Milvus 的边界。

### 10. 当前距离生产还有什么差距？

最重要的不是再加 Agent，而是：

- API Auth / RBAC / Tenant isolation；
- MySQL/ClickHouse 只读适配器 + Secret Manager；
- golden result oracle；
- OpenTelemetry / LLM tracing / metrics dashboard；
- 异步文档摄取任务；
- Redis/DB 持久化 session/document registry。

主动说明这些边界比把 Roadmap 写成已实现更可信。

## Demo 顺序

1. Swagger：展示健康检查、结构化 Schema、统一错误；
2. 上传 `metric_definitions.md`，展示指标知识 RAG；
3. 初始化 `retail_analytics.db`，强调执行默认关闭；
4. 用零售问题生成 SQLite SQL，展示静态校验；
5. 显式开启只读执行，展示结果、Query ID、row cap；
6. 手工提交 `DROP/DELETE/多语句/PRAGMA`，展示 Safety Policy 拒绝；
7. 展示 Text2SQL → SQL Review 的 LangGraph 路径；
8. 运行 `evaluate_text2sql.py`，展示真实 benchmark JSON；
9. 最后展示 Docker Compose 和 GitHub Actions quality gate。

## 简历表达建议

不要写：

> 使用 LangChain、LangGraph、RAG、ChromaDB 构建智能数据助手。

更好的表达：

> 面向企业数据分析构建 AI Copilot，将指标知识 RAG、Text2SQL、确定性 SQL 校验与审核组织为可测试工作流；设计独立 QueryExecutor 端口和默认关闭的只读执行边界，通过白名单、数据库只读模式、查询 deadline、结果行数限制与审计控制模型 SQL 的运行风险，并构建零售 benchmark 分离评估 SQL 有效率、执行成功率、Schema 幻觉、P95 延迟和 Token 成本。
