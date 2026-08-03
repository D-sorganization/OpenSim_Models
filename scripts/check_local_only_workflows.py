#!/usr/bin/env python3
"""Fail when workflows use hosted runners outside the reversible fast lane."""

from __future__ import annotations

from pathlib import Path

WORKFLOW_DIR = Path(".github") / "workflows"
BANNED = (
    "ubuntu-latest",
    "windows-latest",
    "macos-latest",
    "force_cloud",
    "mode=cloud",
    "Routing to GitHub-hosted",
    "using GitHub-hosted",
    "runner=ubuntu-latest",
    "runner=windows-latest",
    "runner=macos-latest",
)


def _hybrid_mode_enabled(text: str) -> bool:
    """Return whether a workflow declares the fail-safe public fast lane."""
    return (
        "CI_RUNNER_MODE != 'local'" in text
        and "ubuntu-latest" in text
        and "d-sorg-fleet" in text
    )


def main() -> int:
    failures: list[str] = []
    if not WORKFLOW_DIR.exists():
        return 0

    for path in sorted(WORKFLOW_DIR.rglob("*")):
        if path.suffix not in {".yml", ".yaml"}:
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8-sig")
        hybrid_mode = _hybrid_mode_enabled(text)
        for line_number, line in enumerate(text.splitlines(), start=1):
            for token in BANNED:
                if token in line:
                    if hybrid_mode and token in {
                        "ubuntu-latest",
                        "runner=ubuntu-latest",
                    }:
                        continue
                    failures.append(
                        f"{path.as_posix()}:{line_number}: "
                        f"banned hosted-runner token {token!r}"
                    )

    if failures:
        print("GitHub-hosted runner routing is outside the approved fast lane.")
        print("\n".join(failures))
        return 1

    print("Workflow runner routing follows the approved hybrid policy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
