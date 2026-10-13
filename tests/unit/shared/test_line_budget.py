"""Monolith budget enforcement: every file in src/ must be under 300 lines.

Ref: Issue #386, AGENTS.md ("No Monoliths: Keep files under 300 lines").
"""

from __future__ import annotations

from pathlib import Path

MAX_SRC_FILE_LINES = 300


def test_src_files_under_300_line_budget() -> None:
    """Enforce the <= 300 lines budget across all src/**/*.py files."""
    repo_root = Path(__file__).resolve().parents[3]
    src_dir = repo_root / "src"
    assert src_dir.is_dir(), f"src directory not found at {src_dir}"

    violations: list[str] = []
    for py_file in sorted(src_dir.rglob("*.py")):
        line_count = len(py_file.read_text(encoding="utf-8").splitlines())
        if line_count > MAX_SRC_FILE_LINES:
            rel_path = py_file.relative_to(repo_root)
            violations.append(
                f"{rel_path}: {line_count} lines (> {MAX_SRC_FILE_LINES})"
            )

    assert not violations, (
        f"{len(violations)} file(s) in src exceed the {MAX_SRC_FILE_LINES}-line budget:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )
