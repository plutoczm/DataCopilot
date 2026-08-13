from pathlib import Path


MANAGE_PY = Path("manage.py")


def test_manage_cli_has_no_stale_public_deployment_entrypoint() -> None:
    content = MANAGE_PY.read_text(encoding="utf-8")

    assert 'subparsers.add_parser("start")' not in content
    assert 'subparsers.add_parser("public")' not in content
    assert "PUBLIC_URL" not in content
    assert "datacopilot-orcin.vercel.app" not in content
    assert "Docker Compose deployment" in content


def test_manage_cli_keeps_supported_local_lifecycle_commands() -> None:
    content = MANAGE_PY.read_text(encoding="utf-8")

    for command in ("stop", "status", "setup"):
        assert f'subparsers.add_parser("{command}")' in content
    assert 'start_parser = subparsers.add_parser("start")' in content
