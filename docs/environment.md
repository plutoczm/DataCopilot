# 运行环境

- Python：3.11 或更高版本。
- 推荐环境：Conda，环境名为 `datacopilot`。
- Node.js：仅静态 Web 或 Vercel 部署时需要。
- Docker：部署后端、前端、ChromaDB 和可选 Ollama 时需要。
- 操作系统：Windows、Linux 或 macOS；生产部署推荐 Linux。

所有缓存、日志、临时文件和持久化数据均放在项目内的 `.runtime/`、`data/` 或 `models/` 目录，避免污染用户目录。
