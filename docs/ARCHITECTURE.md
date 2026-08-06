# 系统架构

DataPilot-AI 是面向数据工程的 AI 智能体平台，采用整洁架构。应用层只依赖领域端口，DeepSeek、Ollama、ChromaDB 等实现可以独立替换。

## 分层结构

```mermaid
flowchart TB
    Presentation[表现层<br/>FastAPI + Streamlit]
    Application[应用层<br/>RAG、Text2SQL、审核、数仓、Agent、评测]
    Domain[领域层<br/>实体 + 端口]
    Infrastructure[基础设施层<br/>大模型、向量库、加载器、Embedding]

    Presentation --> Application
    Application --> Domain
    Infrastructure --> Domain
    Presentation -. 依赖注入 .-> Infrastructure
```

### 表现层

- FastAPI 暴露健康检查、知识库、对话、Agent、Text2SQL、SQL 审核和数仓设计接口。
- Pydantic v2 负责请求、响应和错误格式校验。
- Streamlit 仅通过 HTTP 调用后端，不直接访问大模型、向量库和文件系统。

### 应用层

- RAG：文档摄取、切分、检索、融合、重排、引用和有依据回答。
- Text2SQL：构建 Prompt、解析结构化输出、校验 SQL 并返回优化建议。
- SQL 审核：确定性规则、风险评分和可选大模型解释。
- 数仓设计：生成分层模型、表结构、指标、数据流和 DDL。
- Agent：意图识别、工具调用、多步骤工作流、会话记忆和响应组装。
- 评测：意图准确率、Precision@K、MRR 和工具成功率。

### 领域层

- 定义文档、分块、引用和搜索结果等实体。
- 定义 `LLMProvider` 与 `VectorStore` 端口，使业务逻辑不依赖具体厂商。

### 基础设施层

- DeepSeek Provider：异步对话、流式调用、超时、重试、健康检查和 Token 统计。
- OpenAI Provider：通用 OpenAI 兼容 Chat Completions 客户端，同时服务 OpenAI 云端与 Ollama 本地 OpenAI 兼容接口（无鉴权时自动省略 Authorization 头）。
- Ollama Provider：本地模型对话、流式输出、模型可用性检查（原生 `/api/chat`）。
- Routing Provider：多 LLM 智能路由，按业务任务在本地微调模型与云端模型间分发。
- ChromaDB：向量持久化、相似度检索和元数据过滤。
- 文档加载器：TXT、Markdown、PDF 和 DOCX。
- BGE-M3：文本和查询 Embedding。

## 总体架构

```mermaid
flowchart LR
    Browser[浏览器] --> UI[Streamlit]
    UI --> API[FastAPI]
    API --> Agent[LangGraph Agent]
    Agent --> Tools[LangChain 结构化工具]
    Tools --> RAG[RAG]
    Tools --> T2S[Text2SQL]
    Tools --> Review[SQL 审核]
    Tools --> Warehouse[数仓设计]
    RAG --> VectorPort[VectorStore 端口]
    RAG --> LLMPort[LLMProvider 端口]
    T2S --> LLMPort
    Review --> LLMPort
    Warehouse --> LLMPort
    VectorPort --> Chroma[ChromaDB]
    LLMPort --> DeepSeek[DeepSeek]
    LLMPort --> Ollama[Ollama]
```

## RAG 流程

```mermaid
sequenceDiagram
    participant U as 用户
    participant API as FastAPI
    participant Ingest as 文档摄取
    participant Embed as Embedding
    participant Store as ChromaDB
    participant RAG as RAG 服务
    participant LLM as 大模型

    U->>API: 上传文档
    API->>Ingest: 加载并按结构切分
    Ingest->>Embed: 批量生成向量
    Ingest->>Store: 保存分块、向量和元数据
    U->>API: 提交问题
    API->>RAG: answer
    RAG->>Store: 稠密 ANN 召回
    RAG->>RAG: BM25 + RRF + 轻量重排
    RAG->>RAG: 阈值过滤与上下文组装
    RAG->>LLM: Grounded Prompt
    LLM-->>RAG: 回答
    RAG-->>API: 回答 + 引用 + Token 统计
```

默认使用混合检索，也可以通过 `retrieval_mode=vector` 使用纯向量检索。无候选或候选低于阈值时直接拒答，不调用大模型补全未知事实。

## Agent 流程

```mermaid
flowchart TD
    Query[用户问题] --> Memory[加载会话记忆]
    Memory --> Classify[意图识别]
    Classify -->|RAG| RAGTool[RAG 工具]
    Classify -->|TEXT2SQL| SQLTool[Text2SQL 工具]
    Classify -->|SQL_REVIEW| ReviewTool[SQL 审核工具]
    Classify -->|WAREHOUSE_DESIGN| WarehouseTool[数仓设计工具]
    Classify -->|GENERAL_CHAT| Chat[通用对话]
    SQLTool -->|需要审核| ReviewTool
    RAGTool --> Validate[结果校验]
    SQLTool --> Validate
    ReviewTool --> Validate
    WarehouseTool --> Validate
    Chat --> Validate
    Validate --> Format[格式化响应]
    Format --> Save[保存会话记忆]
    Save --> Response[SSE / JSON 响应]
```

专业节点通过 LangChain `StructuredTool` 调用。每个工具具有 Pydantic 输入模型和 JSON Schema。工作记忆保存在 `AgentState`，短期记忆按 `session_id` 保存，超出窗口的旧消息被压缩为摘要。`recursion_limit` 限制图的最大执行步数。

`validate_result` 节点在领域节点执行后、格式化前运行：对 Text2SQL 复用 `SQLValidator` 做结构/引擎校验，对 SQL 审核重跑规则引擎核对结论一致性（发现幻觉结论），对数仓设计校验分层覆盖率与 DDL，对 RAG 校验引用与回答。校验结果经 `result["validation"]`（或 `metadata["validation"]` 摘要）透出，不阻断主流程。

## 多 LLM 智能路由

```mermaid
flowchart LR
    Task[业务任务] --> TaskBound[TaskBoundLLMProvider]
    TaskBound -->|写入任务上下文| Routing[RoutingLLMProvider]
    Routing -->|专业数据工程任务| Local[本地微调模型<br/>Ollama OpenAI 兼容]
    Routing -->|通用需求| Cloud[云端 DeepSeek/OpenAI]
    Local -->|失败自动降级| Cloud
```

- 领域服务通过组合根注入 `TaskBoundLLMProvider`，在调用时把 `TaskType`（rag/text2sql/sql_review/warehouse_design/general_chat）写入 `ContextVar`。
- `RoutingLLMProvider` 读取上下文，将 Text2SQL、SQL 审核、数仓设计等专业数据工程任务路由到本地微调模型，通用对话与 RAG 路由到云端。
- 本地模型未导入或 Ollama 未启动时自动降级到云端，专业任务不中断。
- 关闭 `DATACOPILOT_LLM__ROUTING_ENABLED` 即回退为单一 provider 行为，与旧版本完全一致。

## Text2SQL 与 SQL 审核

```mermaid
flowchart LR
    NL[自然语言需求] --> Schema[表结构上下文]
    Schema --> Prompt[引擎专用 Prompt]
    Prompt --> LLM[大模型]
    LLM --> Parse[解析结构化输出]
    Parse --> Validate[SQL 静态校验]
    Validate --> Review[可选 SQL 审核]
    Review --> Result[SQL、解释、风险和建议]
```

SQL 校验和规则审核是确定性步骤，不依赖大模型判断核心安全规则。项目当前只生成和审核 SQL，不直接执行生产数据库写操作。

## 部署拓扑

```mermaid
flowchart LR
    User[用户浏览器] --> Frontend[Streamlit :8501]
    Frontend --> Backend[FastAPI :8000]
    Backend --> Chroma[ChromaDB :8001]
    Backend --> DeepSeek[DeepSeek API]
    Backend -. 可选 .-> Ollama[Ollama :11434]
    Ollama --> Finetuned[本地微调模型 GGUF]
    Backend --> OpenAICompat[OpenAI 兼容接口 /v1]
    Backend -. 多 LLM 路由 .-> OpenAICompat
    OpenAICompat -. 指向 .-> Ollama
    Chroma --> VectorData[(data/chromadb)]
    Backend --> Files[(data/uploads)]
    Backend --> Logs[(data/logs)]
```

Docker Compose 为服务配置健康检查、资源限制、统一网络和项目内持久化目录。生产环境还需要反向代理、TLS、认证、限流、集中日志和备份。
