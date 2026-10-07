"""Rust-using workflow jobs must isolate their toolchain homes (RM#2021).

Concurrent jobs on a persistent self-hosted runner share ``~/.rustup`` and
``~/.cargo``; one job's toolchain install can delete binaries from under
another. Every job that touches Rust must point ``RUSTUP_HOME`` and
``CARGO_HOME`` at per-workspace directories.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

WORKFLOWS_DIR = Path(__file__).resolve().parents[2] / ".github" / "workflows"
RUST_PATTERN = re.compile(
    r"\b(cargo|rustup|rustc|maturin|tauri)\b|rust-toolchain", re.IGNORECASE
)
EXPECTED_ENV = {
    "RUSTUP_HOME": "${{ github.workspace }}/.rustup-home",
    "CARGO_HOME": "${{ github.workspace }}/.cargo-home",
}


def _rust_jobs() -> list[tuple[str, str, dict[str, Any]]]:
    found = []
    for path in sorted([*WORKFLOWS_DIR.glob("*.yml"), *WORKFLOWS_DIR.glob("*.yaml")]):
        workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
        for job_id, job in (workflow.get("jobs") or {}).items():
            if RUST_PATTERN.search(yaml.safe_dump(job.get("steps") or [])):
                found.append((path.name, job_id, job))
    return found


def test_rust_jobs_are_detected() -> None:
    """Guard against the scan silently passing on zero Rust jobs."""
    assert any(job_id == "rust-gate" for _, job_id, _ in _rust_jobs())


@pytest.mark.parametrize(
    ("workflow", "job_id", "job"),
    _rust_jobs(),
    ids=lambda v: v if isinstance(v, str) else "",
)
def test_rust_job_isolates_toolchain_homes(
    workflow: str, job_id: str, job: dict[str, Any]
) -> None:
    env = job.get("env") or {}
    for name, expected in EXPECTED_ENV.items():
        assert env.get(name) == expected, f"{workflow}:{job_id} must set {name}"


def test_rust_gate_puts_isolated_cargo_bin_first_on_path() -> None:
    """The installed toolchain must be the one later steps resolve."""
    steps = dict(_rust_jobs_by_id())["rust-gate"]["steps"]
    install = next(s for s in steps if s.get("name") == "Install Rust toolchain")
    assert '"$CARGO_HOME/bin" >> $GITHUB_PATH' in install["run"]
    assert "$HOME/.cargo" not in install["run"]


def _rust_jobs_by_id() -> list[tuple[str, dict[str, Any]]]:
    return [(job_id, job) for _, job_id, job in _rust_jobs()]


def test_rust_gate_fails_when_bootstrap_retries_are_exhausted() -> None:
    """A `&& break || sleep` loop exits 0 after the last sleep; fail explicitly."""
    steps = dict(_rust_jobs_by_id())["rust-gate"]["steps"]
    install = next(s for s in steps if s.get("name") == "Install Rust toolchain")
    assert "|| sleep" not in install["run"]
    assert "exit 1" in install["run"]
