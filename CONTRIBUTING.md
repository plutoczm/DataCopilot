# Contributing

Thanks for your interest in DataPilot-AI.

## Development Setup

```bash
scripts/bootstrap_venv.sh
.venv/bin/pip install -r backend/requirements.txt -r frontend/requirements.txt -r requirements-dev.txt
cp .env.example .env
```

## Branch Workflow

1. Create a feature branch.
2. Keep changes focused.
3. Add or update tests.
4. Run the full test suite.
5. Open a pull request with a concise summary.

## Test Commands

```bash
.venv/bin/python -m pytest -v
.venv/bin/python -m pytest --cov=backend --cov=frontend --cov-report=term-missing --cov-fail-under=85
```

## Architecture Rules

- Application code depends on domain ports, not concrete infrastructure.
- Do not call DeepSeek, ChromaDB, or filesystem internals directly from business services.
- Frontend code must call FastAPI APIs only.
- Keep all runtime data under the project `data/` directory.
- Add tests for new behavior.

## Commit Style

Use clear messages:

```text
feat: add spark plan analyzer
fix: handle missing document metadata
docs: update deployment guide
test: add agent integration workflow
```

## Pull Request Checklist

- [ ] Tests pass.
- [ ] Coverage remains at or above 85%.
- [ ] Docker Compose config validates.
- [ ] No secrets are committed.
- [ ] Documentation is updated when behavior changes.
