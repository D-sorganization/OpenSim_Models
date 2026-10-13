"""Enforce <= 300 line budget on all src/**/*.py files."""

from __future__ import annotations

import sys
from pathlib import Path

MAX_LINES = 300


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    src_dir = repo_root / "src"

    violations: list[str] = []
    for py_file in sorted(src_dir.rglob("*.py")):
        lines = len(py_file.read_text(encoding="utf-8").splitlines())
        if lines > MAX_LINES:
            rel = py_file.relative_to(repo_root)
            violations.append(f"{rel}: {lines} lines (> {MAX_LINES})")

    if violations:
        print(
            f"Error: {len(violations)} file(s) in src exceed the {MAX_LINES}-line budget:"
        )
        for v in violations:
            print(f"  - {v}")
        return 1

    print(
        f"All {len(list(src_dir.rglob('*.py')))} files in src/ are within the {MAX_LINES}-line budget."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
