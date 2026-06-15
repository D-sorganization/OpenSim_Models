from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "check_local_only_workflows.py"
)


@pytest.fixture
def policy_module():
    spec = importlib.util.spec_from_file_location(
        "check_local_only_workflows", SCRIPT_PATH
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_workflow(root: Path, relative_path: str, runs_on: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "name: test",
                "on: push",
                "jobs:",
                "  test:",
                f"    runs-on: {runs_on}",
                "    steps:",
                "      - run: echo ok",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_guard_workflow_cannot_route_to_hosted_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    policy_module,
) -> None:
    monkeypatch.chdir(tmp_path)
    write_workflow(
        tmp_path,
        ".github/workflows/local-only-runner-guard.yml",
        "ubuntu-latest",
    )

    assert policy_module.main() == 1

    output = capsys.readouterr().out
    assert ".github/workflows/local-only-runner-guard.yml" in output
    assert "ubuntu-latest" in output


def test_guard_workflow_can_route_to_fleet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    policy_module,
) -> None:
    monkeypatch.chdir(tmp_path)
    write_workflow(
        tmp_path,
        ".github/workflows/local-only-runner-guard.yml",
        "d-sorg-fleet",
    )

    assert policy_module.main() == 0
    assert "Workflow runner routing is local-only." in capsys.readouterr().out
