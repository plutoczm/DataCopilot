# DataPilot-AI Documentation

**AI Agent Platform for Data Engineering**

This directory contains the publication, deployment, architecture, interview, and release documentation for DataPilot-AI.

The public project name is **DataPilot-AI**. Runtime paths are resolved from the project root so the repository can move between machines without editing generated configuration.

## Documentation Index

- [Architecture](ARCHITECTURE.md): Clean Architecture layers, RAG, Text2SQL, SQL Review, Warehouse Design, LangGraph Agent flow, and Mermaid diagrams.
- [Deployment](DEPLOYMENT.md): Ubuntu 20.04 Docker Compose deployment, health checks, logs, troubleshooting, and backup strategy.
- [API Reference](API_REFERENCE.md): FastAPI endpoint catalog with request and response examples.
- [Interview Guide](INTERVIEW_GUIDE.md): project story, design decisions, trade-offs, demo flow, and common interview questions.
- [Roadmap](ROADMAP.md): completed Phase 1 capabilities and planned Phase 2 extensions.
- [Changelog](CHANGELOG.md): module-by-module implementation summary.
- [Environment Notes](environment.md): local virtual environment and bootstrap notes.
- [Release Checklist](../RELEASE_CHECKLIST.md): final checks before GitHub publication or interview demo.

## Diagram Inventory

The Mermaid diagrams are embedded in [ARCHITECTURE.md](ARCHITECTURE.md):

- Clean Architecture
- System Architecture
- RAG Pipeline
- Text2SQL Flow
- SQL Review Flow
- Warehouse Design Flow
- LangGraph Agent Flow
- Frontend and Backend Interaction
- Deployment Topology

## Screenshot Placeholders

Place demonstration screenshots in `docs/assets/` before publishing:

- `docs/assets/agent-chat.png`
- `docs/assets/knowledge-base.png`
- `docs/assets/text2sql.png`
- `docs/assets/sql-review.png`
- `docs/assets/warehouse-design.png`

## Recommended Reading Order

1. Start with the root [README](../README.md).
2. Read [Architecture](ARCHITECTURE.md) to understand the system boundaries.
3. Use [Deployment](DEPLOYMENT.md) to run the project on Ubuntu 20.04.
4. Use [API Reference](API_REFERENCE.md) for integration and demo requests.
5. Use [Interview Guide](INTERVIEW_GUIDE.md) to prepare the project story.
