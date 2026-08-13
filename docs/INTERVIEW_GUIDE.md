# 项目面试讲解

## 30 秒介绍

DataPilot-AI 是面向企业数据分析场景的 AI Application Copilot。用户可以用自然语言查询指标口径、生成 SQL、审核 SQL，并通过 LangGraph 串联多步骤任务。项目重点不是模型训练，而是把 RAG、Text2SQL、确定性安全校验、Agent 编排、API、Docker 和测试组织成一个可部署、可验证的 AI 应用。

## 业务价值

传统流程通常是：业务提需求 → 数据同学理解指标 → 查表结构 → 写 SQL → 审核风险 → 反复确认。项目尝试把其中重复且规则明确的部分自动化：

- RAG 提供指标口径、Schema 文档等企业知识；
- Text2SQL 把自然语言转成结构化 SQL；
- SQLValidator 和 SQL Review 对模型输出做确定性校验；
- LangGraph 负责组合任务，而不是把所有逻辑塞进一个 Prompt；
- FastAPI、Streamlit、Docker 和 CI 负责把能力变成真正可运行的应用。

## 核心架构取舍

### 为什么采用分层架构？

应用层依赖 `LLMProvider` 和 `VectorStore` 端口，DeepSeek、OpenAI、Ollama、ChromaDB 位于基础设施层。这样业务用例可以用 Fake Provider 测试，模型供应商变化时不需要重写 RAG/Text2SQL 核心逻辑。

### 为什么只保留 DeepSeek / OpenAI / Ollama，而删除任务级多模型路由？

原项目曾加入 `RoutingLLMProvider + TaskBoundLLMProvider`，按 Text2SQL、RAG 等任务选择不同模型。但在没有真实质量、成本或隐私数据证明收益前，这会增加配置、故障路径和测试成本。当前版本把模型选择收敛到应用组合根，业务服务只依赖统一 Provider。

如果未来离线评测证明“某类任务使用特定模型显著更好”，可以重新加入路由，但应由数据驱动，而不是为了展示技术栈。

### 为什么删除微调训练子系统？

目标岗位是 AI 应用开发。微调属于 Model Engineering，独立训练流水线会稀释主项目的应用主线。对这个场景，企业指标、Schema、规范经常变化，优先用 RAG 注入动态私有知识更合理；真正需要稳定改变模型能力时，再把 LoRA/SFT 做成独立项目更容易讲清楚边界。

### 为什么使用 LangGraph？

这里不是因为“Agent 越多越高级”，而是因为部分任务具有明确状态和步骤，例如 Text2SQL → 校验 → SQL Review。LangGraph 能显式表示节点、条件路由、共享状态和终止条件，使路径可测试、可观测。

### 为什么不让 Agent 直接执行生产 SQL？

LLM 输出不应直接拥有生产写权限。当前项目默认只生成、校验和审核 SQL。若以后加入执行器，应使用只读账号、查询超时、最大返回行数、数据源白名单和审计日志。应用层规则只是第一道防线，不能替代数据库权限。

## 高频技术问题

### 1. Agent 如何选择工具？

当前由意图识别进入 RAG、Text2SQL、SQL Review、数仓设计或通用对话节点；组合任务可以先生成 SQL，再进入审核。工具使用 Pydantic 输入模型和 JSON Schema，路由路径写入状态，便于测试和排错。

### 2. 如何降低 RAG 幻觉？

检索阶段使用 Dense + BM25 混合召回、RRF 融合和轻量重排；生成阶段只提供 Top K 上下文并返回引用；低相关度或无候选时拒答。下一步应补答案忠实度和业务问答集的离线评测。

### 3. Text2SQL 如何保证安全？

安全不是靠 Prompt 里写一句“不要生成危险 SQL”。模型返回 JSON 后会经过确定性 SQLValidator：

- 只接受单条 `SELECT/WITH`；
- 拒绝 `INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE/MERGE/GRANT/...`；
- 检查未知表和字段；
- 检查 JOIN 条件和笛卡尔积风险；
- 对 `SELECT *`、缺少分区过滤等给出提示。

真正执行生产查询时仍需数据库只读权限和资源限制。

### 4. 为什么还需要 SQL Review？

Validator 适合确定性安全和结构规则；Review 负责更高层的可读性、性能建议和解释。把两者分开可以避免把所有判断交给 LLM，也避免规则引擎承担无法可靠判断的业务语义。

### 5. 如何管理上下文和记忆？

单次任务使用 `AgentState`；同一 `session_id` 保存最近消息；超出窗口的历史做摘要压缩。当前属于进程内短期记忆，生产长期记忆应使用 Redis/数据库并做租户隔离。

### 6. 如何控制延迟和成本？

文档切分和 Embedding 在摄取阶段完成；查询只放入 Top K 片段；确定性安全检查不调用 LLM；流式接口降低等待感知；外部 Provider 设置超时和有限重试。上线后还应记录 P50/P95 延迟、Token 成本和失败率，再决定缓存或模型分级策略。

### 7. 如何评估项目，而不是凭感觉说“效果很好”？

按任务拆指标：

- Agent：Intent Accuracy、Tool Success Rate；
- RAG：Precision@K、MRR、答案忠实度；
- Text2SQL：Valid SQL Rate、Execution Accuracy、Schema Hallucination Rate；
- Safety：Unsafe SQL Reject Rate、False Reject Rate；
- 工程：P95 Latency、Error Rate、Token/Request。

仓库已有基础 Agent/RAG 指标模型和 `examples/retail_analytics/questions.json` 业务问题集。简历中只应写真实跑出来的数据，不虚构准确率。

### 8. 为什么用 ChromaDB？

对于单机演示和实习项目，ChromaDB 部署成本低，能展示持久化向量检索。因为应用层依赖 VectorStore 端口，规模变大后可以迁移 PGVector、Qdrant、Milvus 等，而不改业务用例。

### 9. 当前项目离生产还有哪些差距？

主要包括：认证/RBAC、租户隔离、真正的只读数据库执行适配器、在线 tracing/metrics、异步文档摄取任务、生产级数据源连接管理，以及更系统的离线评测集。

面试时主动说出边界通常比把所有未来能力包装成“已经实现”更可信。

## Demo 顺序

1. 打开 FastAPI Swagger，先展示健康检查、结构化请求/响应和 API 边界。
2. 上传 `examples/retail_analytics/metric_definitions.md`，说明 GMV、退款率等口径进入知识库。
3. 用 `examples/retail_analytics/questions.json` 中的问题生成 SQL，展示 Schema + 可选 RAG 上下文。
4. 展示 SQLValidator 对危险 SQL、多语句、未知表字段和 JOIN 风险的拒绝/告警。
5. 展示 Text2SQL → SQL Review 的 LangGraph 路由路径和结果校验。
6. 最后展示 Docker Compose、健康检查和 GitHub Actions coverage gate，证明项目不是只在 Notebook 中运行。

## 简历讲项目时避免的说法

不要只说“用了 LangChain、LangGraph、RAG、ChromaDB”。更好的表达是：

> 面向企业数据分析场景实现 AI Copilot，将指标知识检索、Text2SQL、SQL 安全校验和审核组织为可测试的 LangGraph 工作流；通过统一 Provider 端口解耦模型供应商，使用 Docker Compose 与 GitHub Actions 完成部署和质量门禁，并构建零售经营问题集用于离线评测。
