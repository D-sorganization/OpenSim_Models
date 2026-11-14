"""The vendored GAAI framework is gone and must not come back.

The owner retired GAAI fleet-wide (Repository_Management#2720, child #2725).
The checked-in ``.gaai/`` tree is removed; these checks keep it, any daemon
launcher, and live pointers to it from returning.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]

# Files an agent or tool reads on every run. A GAAI pointer here would send it
# to files that no longer exist.
LIVE_ENTRY_POINTS = (
    "CLAUDE.md",
    "AGENTS.md",
    "README.md",
    ".gitignore",
    ".prettierignore",
)

_GAAI = re.compile(r"gaai", re.IGNORECASE)


def test_vendored_tree_is_removed() -> None:
    assert not (REPO_ROOT / ".gaai").exists()


def test_daemon_launchers_are_removed() -> None:
    launchers = [
        p.name
        for pattern in ("*gaai*.sh", "*gaai*.ps1", "*gaai*.cmd")
        for p in REPO_ROOT.glob(pattern)
    ]
    assert launchers == []


@pytest.mark.parametrize("relative_path", LIVE_ENTRY_POINTS)
def test_live_entry_point_does_not_mention_gaai(relative_path: str) -> None:
    path = REPO_ROOT / relative_path
    if not path.exists():
        pytest.skip(f"{relative_path} not present in this repo")
    hits = [
        f"{relative_path}:{number}"
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        )
        if _GAAI.search(line)
    ]
    assert hits == []
