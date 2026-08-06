# 项目面试讲解

## 一句话介绍

DataPilot-AI 是面向数据工程的 AI 智能体平台，用户通过统一对话入口完成知识检索、SQL 生成与审核、数仓建模；系统使用 LangGraph 规划流程、LangChain 结构化工具执行动作、RAG 提供事实依据，并支持 Docker 和本地模型部署。

## 项目价值

- 减少查文档、写 SQL、审核 SQL 和数仓建模之间的工具切换。
- 将大模型的非确定性输出放在 Schema 校验、SQL 规则和 RAG 引用之后。
- 用统一 Provider 端口降低对模型厂商和向量库的绑定。
- 提供可运行、可测试、可观测、可部署的完整项目，而不是单个 Prompt 演示。

## 核心架构取舍

### 为什么采用整洁架构

应用层依赖 `LLMProvider` 和 `VectorStore` 端口，DeepSeek、Ollama、ChromaDB 位于基础设施层。切换模型或向量库时不需要重写核心用例，也便于使用 Fake Provider 做稳定测试。

### 为什么使用 LangGraph

数据工程任务经常包含明确步骤，例如先 Text2SQL，再 SQL 审核。LangGraph 将步骤、条件路由和状态显式化，路由路径可以测试和观测；同时设置递归上限，避免循环调用。

### 为什么使用 LangChain StructuredTool

每个工具拥有名称、中文说明和 Pydantic 参数模型，可生成 JSON Schema。这样无论由确定性路由还是模型原生 Function Calling 选择工具，都复用同一套参数约束。

### 为什么使用 ChromaDB

ChromaDB 轻量、可本地持久化，适合演示和小团队。项目通过端口隔离实现，规模扩大后可以迁移到 Qdrant、Milvus、PGVector 或 Elasticsearch。

### 为什么使用混合检索

稠密向量擅长语义相似，但可能忽略表名、字段名和技术关键词。项目同时执行 Dense ANN 和 BM25，通过 RRF 融合后轻量重排，在语义问题和精确关键词之间取得平衡。

## 高频问题

### 1. Agent 如何选择工具？

当前使用确定性意图路由识别 RAG、Text2SQL、SQL 审核、数仓设计、通用对话和组合任务。LangGraph 根据意图进入对应 StructuredTool；组合请求会先生成 SQL，再进入审核节点。

### 2. 如何避免工具参数错误？

工具调用前由 JSON Schema 描述参数，执行前由 Pydantic 校验类型、范围和必填字段；失败信息进入统一异常体系，并设置有限重试和最大工作流步数。

### 3. 如何降低 RAG 幻觉？

只允许模型根据召回片段回答；返回文档名、分块位置和分数；无候选或低于阈值时拒答。进一步可以加入 Cross-Encoder、答案忠实度评测和人工审核。

### 4. RAG 与微调怎么选？

缺少动态事实或私有知识时用 RAG；缺少稳定风格、格式遵循或特定能力时考虑 SFT/LoRA。项目已实现 RAG，没有把未实现的微调训练写成现有能力。

### 5. 上下文和记忆如何管理？

单次任务使用 `AgentState` 工作记忆；同一 `session_id` 保存最近消息；超出窗口的历史压缩为摘要。当前是进程内短期记忆，生产长期记忆应使用 Redis 或数据库并做租户隔离。

### 6. Text2SQL 如何保证质量？

Prompt 包含引擎、Schema 和结构化输出约束；模型输出解析后执行确定性 SQL 校验，检查语句类型、表字段、JOIN 条件、`SELECT *` 和分区过滤等，再可选进入 SQL 审核。

### 7. 如何控制成本和延迟？

文档切分与 Embedding 离线执行；只把 Top K 片段放入上下文；旧会话做摘要压缩；确定性规则不调用大模型；接口使用 SSE 增量显示。生产环境可增加模型分级、Prompt Cache 和 Batch API。

### 8. 如何评估效果？

按任务拆分指标：意图准确率、RAG Precision@K/MRR/忠实度、SQL 可执行率和结果正确率、工具成功率、P95 延迟、Token 成本及真实用户反馈。项目已提供基础离线指标模型。

### 9. Multi-Agent 如何避免循环？

采用无环拓扑、共享 state、全局步数和深度上限、调用链 ID、明确终止条件。重要操作仍需人工确认，不能仅依赖多个 Agent 互相投票。

### 10. 当前项目边界是什么？

已实现完整单 Agent + 专业工具架构、本地 Ollama 和 Docker 部署。持久化长期记忆、真正多 Agent、微调训练、生产数据库执行和企业鉴权属于后续扩展。

## 演示顺序

1. 打开工作台和 Swagger，展示健康检查与工具 Schema。
2. 上传 Spark AQE 文档，演示混合检索、引用和低分拒答。
3. 输入“统计最近7天活跃用户并检查 SQL”，展示多步骤路由。
4. 输入数仓需求，展示 ODS-DWD-DWS-ADS、指标和 DDL。
5. 使用同一 `session_id` 连续提问，展示短期记忆和清理接口。
6. 展示 `135 passed`、Docker Compose 和 Ollama Provider。
