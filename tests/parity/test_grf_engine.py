"""Real-engine GRF and CoP from ``SmoothSphereHalfSpaceForce`` (issue #391).

A quiet-standing model at rest carries its weight on its feet: the total
vertical ground reaction equals m * g within 2 % and the centre of pressure
lies inside the support polygon of the foot contact spheres. A model lifted
clear of the ground reports zero force and no CoP.

The standing fixture is the gait model in the anatomical neutral pose (every
joint coordinate 0) with its joints locked, placed on the floor and settled
under gravity with only the free root moving, so "at rest" is the engine's own
contact equilibrium, not a constructed one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.tools.ground_reaction import inside_polygon, support_polygon

try:
    import opensim
except ImportError:
    opensim = None

needs_opensim = pytest.mark.skipif(
    opensim is None,
    reason="opensim is not installed in this Python environment",
)

G = 9.80665
GRF_REL_TOL = 0.02  # issue #391 acceptance: total vertical GRF within 2 % of m*g
SETTLE_S = 1.5  # contact transient has decayed below 0.3 % of m*g by 1.2 s
LIFT_M = 0.1  # clearance for the no-contact case


def _standing(tmp_path: Path) -> tuple[Any, Any, Any]:
    """Return (opensim, model, state) of the neutral pose resting on the floor."""
    opensim = pytest.importorskip("opensim")
    opensim.Logger.setLevelString("Error")
    path = tmp_path / "standing.osim"
    path.write_text(EXERCISE_BUILDERS["gait"](), encoding="utf-8")
    model = opensim.Model(str(path))
    state = model.initSystem()
    coords = model.getCoordinateSet()
    for i in range(coords.getSize()):
        if coords.get(i).getName() != "pelvis_ty":
            coords.get(i).setValue(state, 0.0, False)
    _drop_onto_floor(opensim, model, state)
    for i in range(coords.getSize()):
        if not coords.get(i).getName().startswith("pelvis_"):
            coords.get(i).setLocked(state, True)
    return opensim, model, state


def _drop_onto_floor(opensim: Any, model: Any, state: Any) -> None:
    """Lower the root so the lowest foot sphere just touches y = 0."""
    model.realizePosition(state)
    geoms = model.getContactGeometrySet()
    lows = []
    for i in range(geoms.getSize()):
        sphere = opensim.ContactSphere.safeDownCast(geoms.get(i))
        if sphere is not None:
            centre = sphere.getFrame().findStationLocationInGround(
                state, sphere.get_location()
            )
            lows.append(centre.get(1) - sphere.getRadius())
    root = model.getCoordinateSet().get("pelvis_ty")
    root.setValue(state, root.getValue(state) - min(lows), False)


def _settle(opensim: Any, model: Any, state: Any) -> Any:
    """Integrate to SETTLE_S; the caller must keep the returned manager alive.

    ``Manager.integrate`` returns a reference into the manager, so the settled
    state dangles once the manager is garbage collected.
    """
    manager = opensim.Manager(model)
    manager.setIntegratorAccuracy(1e-4)
    state.setTime(0.0)
    manager.initialize(state)
    manager.integrate(SETTLE_S)
    return manager


@needs_opensim
def test_standing_at_rest_carries_body_weight_with_cop_in_support(
    tmp_path: Path,
) -> None:
    from opensim_models.tools.ground_reaction_opensim import (
        foot_contact_points,
        ground_reaction_from_model,
    )

    opensim, model, state = _standing(tmp_path)
    manager = _settle(opensim, model, state)
    state = manager.getState()
    weight = model.getTotalMass(state) * G

    grf = ground_reaction_from_model(model, state)

    assert grf.total.force[2] == pytest.approx(weight, rel=GRF_REL_TOL)
    assert grf.total.cop is not None
    points = foot_contact_points(model, state)
    polygon = support_polygon([p for foot in points.values() for p in foot])
    assert inside_polygon(grf.total.cop[:2], polygon), (grf.total.cop, polygon)
    for foot, reaction in grf.feet.items():
        assert reaction.cop is not None, f"{foot} lost contact while standing"
        assert inside_polygon(reaction.cop[:2], support_polygon(points[foot])), foot
    summed_fz = sum(r.force[2] for r in grf.feet.values())
    assert summed_fz == pytest.approx(grf.total.force[2])


@needs_opensim
def test_lifted_model_reports_no_contact(tmp_path: Path) -> None:
    from opensim_models.tools.ground_reaction_opensim import ground_reaction_from_model

    _, model, state = _standing(tmp_path)
    root = model.getCoordinateSet().get("pelvis_ty")
    root.setValue(state, root.getValue(state) + LIFT_M, False)

    grf = ground_reaction_from_model(model, state)

    assert set(grf.feet) == {"foot_l", "foot_r"}
    assert grf.total.force == (0.0, 0.0, 0.0)
    assert grf.total.cop is None
    for reaction in grf.feet.values():
        assert reaction.force == (0.0, 0.0, 0.0)
        assert reaction.cop is None
