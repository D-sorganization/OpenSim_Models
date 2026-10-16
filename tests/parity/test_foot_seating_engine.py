"""Real OpenSim: seated feet rest on the floor at the start pose (#472).

Every free-root standing model (the four standing lifts and gait) starts with
its soles seated at the contact-law equilibrium depth, so the static contact
force of the engine's own ``SmoothSphereHalfSpaceForce`` carries the lifter and
bar. Measured with OpenSim 4.6 (80 kg, 1.75 m, spec load): 8 spheres at
4.33-4.37 mm for the 200 kg lifts, 4 stance spheres at 3.557 mm for gait; the
engine's vertical contact force matches the weight to 1e-4 (gait) and 7e-6
(lifts).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from opensim_models.exercises import EXERCISE_BUILDERS, SEATED_EXERCISES
from opensim_models.shared.body.foot_seating import (
    contact_heights,
    supported_weight,
)

try:
    import opensim
except ImportError:
    opensim = None

needs_opensim = pytest.mark.skipif(
    opensim is None,
    reason="opensim is not installed in this Python environment",
)

# Same band as the engine-free seating test: 1e7 Pa Hertz spheres (R = 20 mm)
# carrying 80-200 kg on 4-8 spheres seat 3-5 mm deep.
DEPTH_BAND_M = (1.0e-3, 8.0e-3)
# The engine and the XML forward kinematics agree to round-off of the 6-digit
# XML coordinates (1e-6 rad over a ~1 m chain): 1e-6 m.
FK_ATOL_M = 1.0e-6
# Static force balance: the law is the engine's, so only the FK round-off
# above remains (dF/dd ~ 1e5 N/m per sphere x 1e-6 m x 8 spheres ~ 1 N, i.e.
# 5e-4 of a 200 kg weight).
FORCE_RTOL = 1.0e-3


def _engine(tmp_path: Path, exercise: str):  # type: ignore[no-untyped-def]
    xml = EXERCISE_BUILDERS[exercise]()
    path = tmp_path / f"{exercise}.osim"
    path.write_text(xml, encoding="utf-8")
    model = opensim.Model(str(path))
    state = model.initSystem()
    model.realizeDynamics(state)
    tree = ET.fromstring(xml).find("Model")
    assert tree is not None
    return model, state, tree


def _engine_heights(model, state) -> dict[str, float]:  # type: ignore[no-untyped-def]
    heights = {}
    geoms = model.getContactGeometrySet()
    for i in range(geoms.getSize()):
        sphere = opensim.ContactSphere.safeDownCast(geoms.get(i))
        if sphere is None:
            continue
        centre = sphere.getFrame().findStationLocationInGround(
            state, sphere.get_location()
        )
        heights[sphere.getName()] = centre.get(1) - sphere.getRadius()
    return heights


def _vertical_contact_force(model, state) -> float:  # type: ignore[no-untyped-def]
    total = 0.0
    forces = model.getForceSet()
    for i in range(forces.getSize()):
        force = opensim.SmoothSphereHalfSpaceForce.safeDownCast(forces.get(i))
        if force is not None:
            total += force.getRecordValues(state).get(1)
    return total


@needs_opensim
@pytest.mark.parametrize("exercise", SEATED_EXERCISES)
def test_stance_spheres_penetrate_within_band(tmp_path: Path, exercise: str) -> None:
    model, state, tree = _engine(tmp_path, exercise)
    engine = _engine_heights(model, state)
    stance = [-h for h in engine.values() if h < 0.0]
    assert len(stance) == (4 if exercise == "gait" else 8)
    for depth in stance:
        assert DEPTH_BAND_M[0] < depth < DEPTH_BAND_M[1], f"{depth * 1e3:.3f} mm"
    for name, height in contact_heights(tree).items():
        assert engine[name] == pytest.approx(height, abs=FK_ATOL_M), name


@needs_opensim
@pytest.mark.parametrize("exercise", SEATED_EXERCISES)
def test_engine_contact_force_carries_the_weight(tmp_path: Path, exercise: str) -> None:
    model, state, tree = _engine(tmp_path, exercise)
    weight = supported_weight(tree)
    assert _vertical_contact_force(model, state) == pytest.approx(
        weight, rel=FORCE_RTOL
    )
