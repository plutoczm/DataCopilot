# Environment

DataPilot-AI is the public project name for release and resume presentation.
Runtime paths are resolved from the project root. Relative values in `.env`, `docker/.env.production`, and Docker Compose stay portable across machines.

## 2026-06-08

- Project-local virtual environment: `.venv`.
- Created in the same style as `Yolov26`: `/opt/miniconda3/bin/python3 -m venv <project>/.venv`.
- Python version observed from `.venv/pyvenv.cfg`: `3.12.2`.
- Pip cache path for bootstrap: `data/cache/pip`.
- Temporary path for bootstrap: `data/temp`.
- No dependency files for application modules are introduced in module 1.
