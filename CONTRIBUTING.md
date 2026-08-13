# 参与贡献

## 开发环境

```bash
conda env create -f environment.yml
conda activate datacopilot
cp .env.example .env
python -m pytest -q
```

真实 API Key 只保存在本地环境、CI Secret Store 或部署平台，不得提交到仓库。

## 分支流程

1. 从最新主分支创建功能分支。
2. 每次提交只解决一个明确问题，避免把架构重构、依赖升级和功能扩展混在一起。
3. 修改行为时同步补充测试；修改运行方式、接口或质量标准时同步更新文档。
4. 提交前运行与 GitHub Actions 一致的核心门禁：

```bash
python -m pip check
python -m compileall -q backend frontend examples/retail_analytics
docker compose --env-file docker/.env.production config --quiet
python -m pytest -q --cov=backend --cov=frontend --cov-report=term-missing --cov-fail-under=85
```

## 架构约束

- 表现层不得直接访问 ChromaDB、文件系统、数据库执行器或大模型接口。
- 应用层依赖领域端口，不直接依赖具体基础设施实现。
- 新增 Provider 时实现统一的 `LLMProvider`、`VectorStore`、`SchemaCatalog` 或 `QueryExecutor` 端口，不把 provider 分支扩散到业务代码。
- 工具输入和 API 边界使用 Pydantic Schema；外部模型输出在进入业务逻辑前必须解析和校验。
- 确定性安全规则不得依赖 LLM 自评。SQL allow/deny、Schema grounding、执行权限等边界必须由应用策略或数据库原生权限保证。
- Query Execution 不注册成自主 Agent Tool。真实数据库执行保留为用户显式动作，并经过 datasource allowlist、read-only policy、row cap、timeout 和审计。
- Text2SQL 基于 datasource 生成时必须保留 Schema provenance；执行生成 SQL 时继续使用 generation-time fingerprint 作为 schema-drift precondition。
- 不在业务代码中硬编码密钥、绝对路径、客户端提交的数据库连接串或生产地址。
- 不为简历技术栈数量引入没有业务收益、没有测试或没有真实调用链的组件。

## AI 行为变更验收

以下改动不仅需要单元测试，还需要重新运行 Text2SQL benchmark：

- LLM provider / model 变更；
- Text2SQL Prompt 或输出解析变更；
- Schema grounding / SQLValidator 规则变更；
- RAG 检索、重排、阈值或业务知识变更；
- Golden SQL / Safety case / Result Oracle 变更。

固定 demo 数据后运行：

```bash
python examples/retail_analytics/setup_demo_db.py --force
python examples/retail_analytics/evaluate_text2sql.py
python examples/retail_analytics/check_benchmark_report.py \
  data/evaluation/retail_text2sql_report.json
```

不要把以下概念混为一个指标：

- pytest coverage：代码路径是否被测试；
- Valid SQL / Execution Success：SQL 是否可接受、可运行；
- Business Result Accuracy：业务结果是否与 Golden Result 一致；
- Safety metrics：不安全请求是否被稳定拒绝。

任何出现在 README、PR 或简历中的模型效果数字都应来自固定配置下保存的真实 benchmark artifact。

## 提交格式

```text
feat: 新增功能
fix: 修复问题
docs: 更新文档
test: 补充测试
refactor: 重构但不改变行为
ci: 调整持续集成或发布门禁
build: 调整依赖或容器构建配置
```

## 合并请求检查

- [ ] 代码和提交内容聚焦于当前任务。
- [ ] 接口兼容性与安全边界已经确认。
- [ ] 单元测试和集成测试通过，coverage 未跌破门槛。
- [ ] `pip check` 与 Docker Compose 配置验证通过。
- [ ] AI 行为发生变化时，已附真实 benchmark / quality gate 结果。
- [ ] 新增核心模块有测试覆盖，不提交未接入或未验证的“基础设施占位代码”。
- [ ] 文档准确区分已实现能力、真实评测结果和规划能力。
