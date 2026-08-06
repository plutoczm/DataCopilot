# 变更记录

## 当前开发版本

### 智能体

- 使用 LangChain `StructuredTool` 注册 RAG、Text2SQL、SQL 审核和数仓设计工具。
- 为所有工具增加 Pydantic JSON Schema 参数校验和工具目录接口。
- 增加会话短期记忆、旧消息摘要压缩和会话清理。
- 增加 LangGraph 最大执行步数，防止循环调用。
- SSE 改为增量分片输出。
- 新增 `validate_result` 结果校验节点：SQL 结构/引擎校验、SQL 审核结论与规则引擎一致性核对、数仓分层覆盖率与 DDL 检查、RAG 引用与回答检查，校验摘要透出到 `metadata.validation`。

### 多 LLM 智能路由

- 新增通用 OpenAI 兼容 Provider，同时服务 OpenAI 云端与 Ollama 本地 OpenAI 兼容接口。
- 新增 `TaskBoundLLMProvider` + `RoutingLLMProvider`：专业数据工程任务（Text2SQL/SQL 审核/数仓设计）路由到本地微调模型，通用需求走云端，本地故障自动降级。
- 新增 `LocalModelSettings` 与 `DATACOPILOT_LLM__ROUTING_*` 配置，默认关闭路由，行为与旧版本一致。

### RAG 检索

- 新增纯向量与混合检索模式。
- 混合检索使用稠密 ANN、BM25、RRF 融合和轻量词项重排。
- 保留分数阈值、无召回拒答和引用来源。
- 首次启动时幂等创建默认知识库集合。

### 大模型与部署

- 新增 Ollama Provider，可与 DeepSeek 通过环境变量切换。
- Docker Compose 增加 Ollama Provider 配置。
- 新增意图准确率、Precision@K、MRR 和工具成功率评测模型。
- 完成说明文档、代码注释和 OpenAPI 文案中文化。

### 验证

- 全量自动化测试：`176 passed`。
- Python 编译、Docker Compose 配置和健康检查通过。

## 0.1.0

- 建立项目骨架、配置系统和结构化日志。
- 实现知识库 RAG、ChromaDB 和 DeepSeek Provider。
- 实现 FastAPI、Text2SQL、SQL 审核和数仓设计。
- 实现 LangGraph 路由、Streamlit 前端和 Docker Compose。
- 建立单元、接口、基础设施、部署和集成测试。
