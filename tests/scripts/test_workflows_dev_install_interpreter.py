"""Jobs that install the ``dev`` extra must provision their own interpreter.

The ``dev`` extra pulls in ``opensim``, which publishes wheels for a few
CPython versions only. A job that takes whatever ``python`` the runner image
has breaks when the image moves to a version without a wheel (CPython 3.14 on
GitHub-hosted runners, November 2026). ``actions/setup-python`` fixes the
version instead.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

WORKFLOW = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci-standard.yml"
)


def _dev_install_jobs() -> dict[str, list[dict[str, Any]]]:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return {
        job_id: job.get("steps") or []
        for job_id, job in (workflow.get("jobs") or {}).items()
        if any("[dev]" in str(step.get("run", "")) for step in job.get("steps") or [])
    }


def test_dev_install_jobs_are_detected() -> None:
    """Guard against the scan silently passing on zero jobs."""
    assert {"quality-gate", "tests", "model-pack-smoke"} <= set(_dev_install_jobs())


def test_dev_install_jobs_set_up_python_before_installing() -> None:
    missing = []
    for job_id, steps in _dev_install_jobs().items():
        install_at = next(
            i for i, step in enumerate(steps) if "[dev]" in str(step.get("run", ""))
        )
        provisioned = any(
            str(step.get("uses", "")).startswith("actions/setup-python@")
            and (step.get("with") or {}).get("python-version")
            for step in steps[:install_at]
        )
        if not provisioned:
            missing.append(job_id)
    assert missing == [], f"jobs install the dev extra on an unpinned Python: {missing}"
