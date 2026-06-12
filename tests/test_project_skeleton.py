from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_required_top_level_directories_exist() -> None:
    required_directories = [
        "backend",
        "frontend",
        "knowledge_base",
        "data/chromadb",
        "data/uploads",
        "data/logs",
        "data/cache",
        "data/embeddings",
        "data/temp",
        "docker",
        "docs",
        "tests",
        "scripts",
        "models",
    ]

    missing = [
        directory
        for directory in required_directories
        if not (PROJECT_ROOT / directory).is_dir()
    ]

    assert missing == []


def test_backend_and_frontend_package_boundaries_exist() -> None:
    required_files = [
        "backend/app/__init__.py",
        "backend/app/main.py",
        "backend/app/presentation/__init__.py",
        "backend/app/presentation/api/__init__.py",
        "backend/app/application/__init__.py",
        "backend/app/domain/__init__.py",
        "backend/app/infrastructure/__init__.py",
        "backend/app/core/__init__.py",
        "frontend/app.py",
        "frontend/pages/.gitkeep",
        "frontend/components/.gitkeep",
        "frontend/services/.gitkeep",
        "scripts/bootstrap_venv.sh",
        "scripts/dev.sh",
        "scripts/stop-dev.sh",
        "docs/environment.md",
    ]

    missing = [file for file in required_files if not (PROJECT_ROOT / file).is_file()]

    assert missing == []


def test_development_scripts_use_project_local_runtime_paths() -> None:
    dev_script = PROJECT_ROOT / "scripts" / "dev.sh"
    stop_script = PROJECT_ROOT / "scripts" / "stop-dev.sh"

    dev_content = dev_script.read_text(encoding="utf-8")
    stop_content = stop_script.read_text(encoding="utf-8")

    assert "PROJECT_ROOT=" in dev_content
    assert "BACKEND_PORT=\"${BACKEND_PORT:-8000}\"" in dev_content
    assert "FRONTEND_PORT=\"${FRONTEND_PORT:-8502}\"" in dev_content
    assert "BACKEND_URL=" in dev_content
    assert "http://127.0.0.1:${BACKEND_PORT}" in dev_content
    assert "data/logs" in dev_content
    assert "data/temp" in dev_content
    assert "trap handle_stop INT TERM" in dev_content
    assert "trap cleanup EXIT" in dev_content
    assert "wait_for_exit" in dev_content
    assert "按 Ctrl+C 停止服务" in dev_content
    assert "frontend-dev.pid" in stop_content
    assert "backend-dev.pid" in stop_content


def test_project_local_virtual_environment_matches_yolov26_style() -> None:
    pyvenv_config = PROJECT_ROOT / ".venv" / "pyvenv.cfg"

    assert pyvenv_config.is_file()

    config_text = pyvenv_config.read_text(encoding="utf-8")

    assert "version = 3.12.2" in config_text
    assert "include-system-site-packages = false" in config_text
    assert f"{PROJECT_ROOT}/.venv" in config_text


def test_runtime_storage_directories_stay_inside_project_root() -> None:
    runtime_directories = [
        PROJECT_ROOT / "data" / "chromadb",
        PROJECT_ROOT / "data" / "uploads",
        PROJECT_ROOT / "data" / "logs",
        PROJECT_ROOT / "data" / "cache",
        PROJECT_ROOT / "data" / "embeddings",
        PROJECT_ROOT / "data" / "temp",
        PROJECT_ROOT / "models",
    ]

    for directory in runtime_directories:
        assert directory.resolve().is_relative_to(PROJECT_ROOT.resolve())
        assert directory.is_dir()
