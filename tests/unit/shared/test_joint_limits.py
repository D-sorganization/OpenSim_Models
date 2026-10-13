"""Verify joint limits in the generated body model match the shared parity standard.

Ref: Issue #393 ("Derive joint limits from the bundle, not rounded-radian literals").
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from opensim_models.shared.body.body_model import create_full_body
from opensim_models.shared.parity.standard import JOINT_LIMITS


def _canonical_coord_key(coord_name: str) -> str:
    """Map coordinate name (e.g. 'shoulder_l_flex') to JOINT_LIMITS key ('shoulder_flex')."""
    base = re.sub(r"_[lr]_", "_", coord_name)
    if base == "wrist_deviation":
        base = "wrist_deviate"
    elif base == "ankle_inversion":
        base = "ankle_invert"
    return base


def test_every_joint_range_matches_bundle_limits_within_1e9() -> None:
    """Every coordinate range in the generated full-body model must equal the bundle limit within 1e-9 rad."""
    bodyset = ET.Element("BodySet")
    jointset = ET.Element("JointSet")
    create_full_body(bodyset, jointset)

    coords_found = 0
    for coord in jointset.iter("Coordinate"):
        name = coord.get("name")
        assert name is not None
        if name.startswith("pelvis_"):
            continue  # Root 6-DOF coordinates are unconstrained

        range_el = coord.find("range")
        assert range_el is not None, f"Coordinate {name} has no <range> element"
        assert range_el.text is not None

        lo, hi = (float(v) for v in range_el.text.split())
        key = _canonical_coord_key(name)
        assert key in JOINT_LIMITS, f"Coordinate {name} (key {key}) not in JOINT_LIMITS"

        exp_lo, exp_hi = JOINT_LIMITS[key]
        assert abs(lo - exp_lo) < 1e-9, (
            f"{name} range_min {lo} != bundle limit {exp_lo} (diff={abs(lo - exp_lo):.2e})"
        )
        assert abs(hi - exp_hi) < 1e-9, (
            f"{name} range_max {hi} != bundle limit {exp_hi} (diff={abs(hi - exp_hi):.2e})"
        )
        coords_found += 1

    assert coords_found >= 28, f"Expected at least 28 coordinates, found {coords_found}"


@pytest.mark.parametrize(
    "filename",
    ["axial_skeleton.py", "body_model.py", "appendicular.py"],
)
def test_no_numeric_limit_literals_remain(filename: str) -> None:
    """Verify rounded-radian numeric literals for limits are removed from body model files."""
    repo_root = Path(__file__).resolve().parents[3]
    file_path = repo_root / "src" / "opensim_models" / "shared" / "body" / filename
    if not file_path.is_file():
        return

    content = file_path.read_text(encoding="utf-8")

    # Known previous rounded literals: -0.5236, 0.5236, 0.7854, 2.0944, -1.0472, 3.1416, 2.618, 0.8727, -1.2217, 1.2217
    banned_literals = [
        "-0.5236",
        "0.7854",
        "2.0944",
        "-1.0472",
        "3.1416",
        "2.618",
        "-2.618",
        "0.8727",
        "-1.2217",
        "1.2217",
        "-0.3491",
    ]
    for lit in banned_literals:
        # Check if literal appears outside comments
        lines = [
            line for line in content.splitlines() if not line.strip().startswith("#")
        ]
        matches = [line for line in lines if lit in line]
        assert not matches, (
            f"Found numeric limit literal {lit!r} in {filename}:\n" + "\n".join(matches)
        )
