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
    assert "approved hybrid policy" in capsys.readouterr().out


def test_guard_allows_fail_safe_reversible_hosted_expression(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    policy_module,
) -> None:
    monkeypatch.chdir(tmp_path)
    write_workflow(
        tmp_path,
        ".github/workflows/ci-standard.yml",
        "${{ !github.event.repository.private && vars.CI_RUNNER_MODE != 'local' && 'ubuntu-latest' || 'd-sorg-fleet' }}",
    )

    assert policy_module.main() == 0


def test_repository_ci_picker_is_zero_polling_and_heavy_rust_stays_local() -> None:
    import yaml  # noqa: PLC0415

    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load(
        (root / ".github/workflows/ci-standard.yml").read_text(encoding="utf-8")
    )
    jobs = workflow["jobs"]
    scripts = "\n".join(step.get("run", "") for step in jobs["pick-runner"]["steps"])

    assert "CI_RUNNER_MODE != 'local'" in jobs["pick-runner"]["runs-on"]
    assert "gh api" not in scripts
    assert jobs["tests"]["strategy"]["max-parallel"] == 3
    assert "d-sorg-fleet" in jobs["rust-gate"]["runs-on"]
