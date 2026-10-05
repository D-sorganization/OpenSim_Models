"""Real-engine ground contact: free-root models start resting on y = 0."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

from opensim_models.exercises import EXERCISE_BUILDERS

needs_opensim = pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="the opensim pip wheel is published for CPython 3.11+ only",
)

FREE_ROOT = [e for e in EXERCISE_BUILDERS if e != "bench_press"]
TOL = 0.005  # 5 mm
BODY_MASS = 80.0
G = 9.80665
# Static placement with no velocity: measured support forces are 0.1-0.2 body
# weights (max 145 N for an 80 kg model), never a 1e5 N blow-up.
MAX_GRF_BODY_WEIGHTS = 1.0


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
    weight = BODY_MASS * G
    assert -1e-6 <= total_fy <= MAX_GRF_BODY_WEIGHTS * weight, (
        f"{exercise}: vertical ground force {total_fy:.1f} N vs weight {weight:.1f} N"
    )
