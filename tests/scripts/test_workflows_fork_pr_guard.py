"""This repository's real workflows must not run fork PR code on the fleet.

Runs the vendored checker (``scripts/fork_pr_runner_guard.py``, canonical in
Repository_Management, RM#1989) against the actual ``.github/workflows``.
"""

from __future__ import annotations

from pathlib import Path

from scripts import fork_pr_runner_guard as guard

WORKFLOWS_DIR = Path(__file__).resolve().parents[2] / ".github" / "workflows"


def test_workflows_dir_exists() -> None:
    """Guard against the scan silently passing on a missing directory."""
    assert any(WORKFLOWS_DIR.glob("*.yml"))


def test_no_workflow_runs_fork_pr_code_on_self_hosted() -> None:
    """Every fleet-capable job is fork-guarded or fork-routed to hosted."""
    assert guard.find_violations(WORKFLOWS_DIR) == []
