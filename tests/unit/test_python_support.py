# SPDX-License-Identifier: MIT
"""Verification of Python version requirements and CI matrix consistency (#397)."""

from __future__ import annotations

import sys
from pathlib import Path

import tomllib
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_python_version_is_supported() -> None:
    """The running Python interpreter must be 3.11+."""
    assert sys.version_info >= (3, 11), (
        f"OpenSim_Models requires Python >=3.11, running on {sys.version}"
    )


def test_pyproject_requires_python_311() -> None:
    """pyproject.toml must declare requires-python >= 3.11."""
    pyproject_path = REPO_ROOT / "pyproject.toml"
    assert pyproject_path.is_file(), "pyproject.toml not found"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    requires_python = data["project"]["requires-python"]
    assert requires_python == ">=3.11"

    classifiers = data["project"].get("classifiers", [])
    assert "Programming Language :: Python :: 3.10" not in classifiers
    assert "Programming Language :: Python :: 3.11" in classifiers
    assert "Programming Language :: Python :: 3.12" in classifiers


def test_ci_matrix_does_not_contain_310() -> None:
    """ci-standard.yml test matrix must only test supported Python versions (3.11, 3.12)."""
    workflow_path = REPO_ROOT / ".github" / "workflows" / "ci-standard.yml"
    assert workflow_path.is_file(), "ci-standard.yml not found"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    matrix = workflow["jobs"]["tests"]["strategy"]["matrix"]
    python_versions = matrix["python"]
    assert "3.10" not in python_versions
    assert python_versions == ["3.11", "3.12"]


def test_spec_declares_python_311() -> None:
    """SPEC.md must declare Primary language as Python 3.11+."""
    spec_path = REPO_ROOT / "SPEC.md"
    assert spec_path.is_file(), "SPEC.md not found"
    content = spec_path.read_text(encoding="utf-8")
    assert (
        "| Primary language  | Python 3.11+                                        |"
        in content
    )
