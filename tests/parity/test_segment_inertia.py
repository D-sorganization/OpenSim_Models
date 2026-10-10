"""Tests for segment inertia matching the cross-repo parity standard (#392).

Verifies that segment radius is computed from the standard's ``radius_frac``
(not from uniform tissue density) and that resulting segment inertias match
the shared standard within 1e-6 relative.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.shared.body import BodyModelSpec, create_full_body
from opensim_models.shared.parity._canonical import conformance
from opensim_models.shared.utils.geometry import (
    cylinder_inertia,
    rectangular_prism_inertia,
)

try:
    import opensim
except ImportError:
    opensim = None

needs_opensim = pytest.mark.skipif(
    opensim is None or sys.version_info < (3, 11),
    reason="the opensim pip wheel is published for CPython 3.11+ only",
)

STD = conformance.load_standard()
EXPECTED_SEGMENTS = conformance.expected_segments(STD)


def _compute_standard_inertia(
    segment_name: str,
    total_mass: float = 80.0,
    height: float = 1.75,
) -> tuple[float, float, float]:
    """Compute shared-standard principal inertia (ixx, iyy, izz) from radius_frac."""
    base_name = segment_name.removesuffix("_l").removesuffix("_r")
    seg_info = STD["anthropometrics"]["segments"][base_name]

    mass = total_mass * float(seg_info["mass_frac"])
    length = height * float(seg_info["length_frac"])
    radius = height * float(seg_info["radius_frac"])

    if base_name in ("pelvis", "torso"):
        return rectangular_prism_inertia(mass, radius * 2, length, radius * 2)
    return cylinder_inertia(mass, radius, length)


@pytest.mark.parametrize("segment_name", sorted(EXPECTED_SEGMENTS.keys()))
def test_generated_body_inertia_matches_standard(segment_name: str) -> None:
    """Inertia from create_full_body matches the shared standard within 1e-6."""
    bodyset = ET.Element("BodySet")
    jointset = ET.Element("JointSet")
    spec = BodyModelSpec(total_mass=80.0, height=1.75)
    bodies = create_full_body(bodyset, jointset, spec)

    assert segment_name in bodies, f"{segment_name} missing from created bodies"
    body_el = bodies[segment_name]
    inertia_el = body_el.find("inertia")
    assert inertia_el is not None and inertia_el.text, f"no inertia on {segment_name}"

    moments = [float(x) for x in inertia_el.text.split()[:3]]
    expected = _compute_standard_inertia(segment_name, spec.total_mass, spec.height)

    assert moments[0] == pytest.approx(expected[0], rel=1e-6, abs=1e-6)
    assert moments[1] == pytest.approx(expected[1], rel=1e-6, abs=1e-6)
    assert moments[2] == pytest.approx(expected[2], rel=1e-6, abs=1e-6)


@pytest.mark.parametrize("segment_name", sorted(EXPECTED_SEGMENTS.keys()))
def test_exercise_model_inertia_matches_standard(segment_name: str) -> None:
    """Inertia from generated exercise model (.osim XML) matches shared standard."""
    root = ET.fromstring(EXERCISE_BUILDERS["squat"]())
    bodies = {b.get("name"): b for b in root.iter("Body")}

    assert segment_name in bodies, f"{segment_name} missing from exercise model"
    body_el = bodies[segment_name]
    inertia_el = body_el.find("inertia")
    assert inertia_el is not None and inertia_el.text, f"no inertia on {segment_name}"

    moments = [float(x) for x in inertia_el.text.split()[:3]]
    expected = _compute_standard_inertia(segment_name)

    assert moments[0] == pytest.approx(expected[0], rel=1e-6, abs=1e-6)
    assert moments[1] == pytest.approx(expected[1], rel=1e-6, abs=1e-6)
    assert moments[2] == pytest.approx(expected[2], rel=1e-6, abs=1e-6)


@needs_opensim
@pytest.mark.parametrize("segment_name", sorted(EXPECTED_SEGMENTS.keys()))
def test_real_engine_segment_inertia_matches_standard(
    tmp_path: Path, segment_name: str
) -> None:
    """Real OpenSim engine reports segment inertia matching shared standard."""
    osim_path = tmp_path / "squat.osim"
    osim_path.write_text(EXERCISE_BUILDERS["squat"](), encoding="utf-8")

    model = opensim.Model(str(osim_path))
    model.initSystem()

    body = model.getBodySet().get(segment_name)
    assert body is not None, f"Body {segment_name} not found in OpenSim model"

    moments = body.getInertia().getMoments()
    expected = _compute_standard_inertia(segment_name)

    assert moments.get(0) == pytest.approx(expected[0], rel=1e-6, abs=1e-6)
    assert moments.get(1) == pytest.approx(expected[1], rel=1e-6, abs=1e-6)
    assert moments.get(2) == pytest.approx(expected[2], rel=1e-6, abs=1e-6)
