"""Real-engine ground contact: free-root models start resting on y = 0."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from opensim_models.exercises import EXERCISE_BUILDERS, SEATED_EXERCISES
from opensim_models.shared.body.foot_seating import supported_weight

pytestmark = pytest.mark.requires_opensim

try:
    import opensim
except ImportError:
    opensim = None

needs_opensim = pytest.mark.skipif(
    opensim is None,
    reason="opensim is not installed in this Python environment",
)

FREE_ROOT = [e for e in EXERCISE_BUILDERS if e != "bench_press"]
TOL = 0.005  # 5 mm
# Static placement with no velocity: flush (unseated) feet carry 0.1-0.3 of
# the supported weight, never a 1e5 N blow-up; seated feet (#472) carry the
# supported weight (lifter plus bar) to the engine/XML round-off.
MAX_GRF_BODY_WEIGHTS = 1.0
SEATED_FORCE_RTOL = 1e-3


def _load(tmp_path: Path, exercise: str):  # type: ignore[no-untyped-def]
    import opensim

    path = tmp_path / f"{exercise}.osim"
    path.write_text(EXERCISE_BUILDERS[exercise](), encoding="utf-8")
    model = opensim.Model(str(path))
    return opensim, model, model.initSystem()


def _sphere_lows(opensim, model, state) -> list[float]:  # type: ignore[no-untyped-def]
    model.realizePosition(state)
    lows = []
    geoms = model.getContactGeometrySet()
    for i in range(geoms.getSize()):
        sphere = opensim.ContactSphere.safeDownCast(geoms.get(i))
        if sphere is None:
            continue
        centre = sphere.getFrame().findStationLocationInGround(
            state, sphere.get_location()
        )
        lows.append(centre.get(1) - sphere.getRadius())
    return lows


@needs_opensim
@pytest.mark.parametrize("exercise", FREE_ROOT)
def test_feet_do_not_start_inside_the_ground(tmp_path: Path, exercise: str) -> None:
    opensim, model, state = _load(tmp_path, exercise)
    lows = _sphere_lows(opensim, model, state)
    assert len(lows) == 8
    assert min(lows) >= -TOL, f"{exercise}: sphere {-min(lows):.3f} m deep"
    # Seated sit_to_stand included: its feet rest on the floor too (#383).
    assert min(lows) == pytest.approx(0.0, abs=TOL), "feet float above y=0"


@needs_opensim
@pytest.mark.parametrize("exercise", FREE_ROOT)
def test_ground_force_is_finite_and_bounded(tmp_path: Path, exercise: str) -> None:
    opensim, model, state = _load(tmp_path, exercise)
    model.realizeAcceleration(state)
    forces = model.getForceSet()
    total_fy = 0.0
    for i in range(forces.getSize()):
        force = opensim.SmoothSphereHalfSpaceForce.safeDownCast(forces.get(i))
        if force is None:
            continue
        values = force.getRecordValues(state)
        comps = [values.get(k) for k in range(values.size())]
        assert all(math.isfinite(c) for c in comps), force.getName()
        total_fy += comps[1]
    tree = ET.fromstring(EXERCISE_BUILDERS[exercise]()).find("Model")
    assert tree is not None
    weight = supported_weight(tree)
    if exercise in SEATED_EXERCISES:
        assert total_fy == pytest.approx(weight, rel=SEATED_FORCE_RTOL)
        return
    assert -1e-6 <= total_fy <= MAX_GRF_BODY_WEIGHTS * weight, (
        f"{exercise}: vertical ground force {total_fy:.1f} N vs weight {weight:.1f} N"
    )
