# DataPilot-AI 发布检查清单

该清单用于发布候选版本或准备可公开演示的简历版本。代码测试、运行时安全与 AI 效果分别验收，不能用其中一项替代另一项。

## 1. 仓库与配置

- [ ] 不存在误提交的密钥、日志、缓存、数据库文件、模型权重或 benchmark 临时产物。
- [ ] `.env.example` 与 `docker/.env.production` 只包含安全默认值和空密钥占位。
- [ ] README、启动方式、架构说明与当前代码一致，不保留已删除组件的使用说明。
- [ ] GitHub Actions 使用最小权限，并且最新 `ci / quality` 为绿色。
- [ ] Dependabot 已覆盖 Python 与 GitHub Actions 依赖。

## 2. 后端与运行时

- [ ] `/health` 返回可解释的服务、LLM 与 Vector Store 状态。
- [ ] `/docs` 与 OpenAPI Schema 可以打开。
- [ ] 当前选定的 DeepSeek / OpenAI / Ollama provider 健康检查符合部署预期。
- [ ] 默认知识库集合可以创建、摄取、检索和删除文档。
- [ ] 结构化日志包含 request ID / trace ID；错误响应不泄漏 secret、stack trace 或数据库路径。

## 3. Text2SQL 与数据安全

- [ ] Datasource Schema 可以自动发现，并返回稳定 `schema_fingerprint`。
- [ ] Text2SQL datasource 模式不要求客户端提交数据库 URL/path。
- [ ] SQLValidator 对未知表、未知字段、危险语句、笛卡尔积等规则按预期工作。
- [ ] Query Execution 在生产默认保持关闭。
- [ ] 显式启用执行后，只接受服务端白名单 datasource，并保持 read-only、row cap 与 timeout。
- [ ] 执行生成 SQL 时携带 generation-time schema fingerprint；Schema 变化时返回 `schema_drift`，不盲目执行旧 SQL。
- [ ] reader / analyst / admin 权限边界符合预期，Query Execution 至少需要 analyst。

## 4. RAG 与 Agent

- [ ] TXT / Markdown / PDF / DOCX 摄取链路可用。
- [ ] Dense + BM25 / RRF 混合检索可用；低相关结果触发拒答。
- [ ] 回答包含 citation / provenance，而不是只返回无来源文本。
- [ ] Agent 路由、会话记忆、最大执行步数与结果校验工作正常。
- [ ] 数据库执行没有被注册成自主 Agent Tool，仍要求用户显式触发。

## 5. Docker 与部署

- [ ] `docker compose --env-file docker/.env.production config --quiet` 通过。
- [ ] backend / frontend healthcheck 通过。
- [ ] 可选 Ollama profile 可以按需启动。
- [ ] backend / frontend 以非 root 用户运行。
- [ ] 容器 CPU / memory 边界符合目标机器预算。
- [ ] 数据目录持久化路径与权限正确。

## 6. 代码质量门禁

```bash
python -m pip check
python -m compileall -q backend frontend examples/retail_analytics
docker compose --env-file docker/.env.production config --quiet
python -m pytest -q --cov=backend --cov=frontend --cov-report=term-missing --cov-fail-under=85
```

- [ ] `pip check` 无 broken requirements。
- [ ] 全量测试通过。
- [ ] 总覆盖率达到 85% 门槛。
- [ ] 单元/集成测试不要求真实外部 LLM API Key。

## 7. AI 效果门禁

先准备可复现零售数据：

```bash
python examples/retail_analytics/setup_demo_db.py --force
```

在固定模型、固定配置、固定 datasource 上运行真实 benchmark：

```bash
python examples/retail_analytics/evaluate_text2sql.py
```

需要评估业务知识增强时，再运行：

```bash
python examples/retail_analytics/evaluate_text2sql.py --use-rag
```

然后检查生成的 benchmark artifact：

```bash
python examples/retail_analytics/check_benchmark_report.py \
  data/evaluation/retail_text2sql_report.json
```

- [ ] Generation Success Rate 达到门禁。
- [ ] Valid SQL Rate 达到门禁。
- [ ] Business Result Accuracy 达到门禁；不以“SQL 能执行”冒充业务正确。
- [ ] Schema Hallucination Rate 不超过门禁。
- [ ] Safety Decision Accuracy / Unsafe Rejection Rate 达到门禁。
- [ ] 失败 case 可以从报告中定位，且没有只统计成功样本。
- [ ] 简历或 README 中出现的模型效果数字来自保存的真实 benchmark 报告，而不是测试代码或人工估计。

## 8. 演示验收

- [ ] 演示知识库：上传文档 → 检索 → 带 citation 回答。
- [ ] 演示 Text2SQL：选择 datasource → 自动发现 Schema → 生成 → 校验 / Review。
- [ ] 在显式开启 read-only execution 后，演示生成 SQL 的受治理执行与结果返回。
- [ ] 演示 Schema drift 被拒绝执行，而不是继续跑旧 SQL。
- [ ] 展示 Golden Result benchmark 与 AI Quality Gate 输出。
- [ ] 展示 Swagger/OpenAPI、CI、coverage 与 Docker 运行状态。
