"""OpenSim adapter: GRF and CoP from ``SmoothSphereHalfSpaceForce`` records.

Issue #391. Thin by design: it reads each contact force's ``getRecordValues``
and the contact body of its sphere, rotates the engine's Y-up vectors into the
canonical Z-up frame with the vendored bundle's ``to_canonical`` rotation, and
hands the result to the engine-free math in ``ground_reaction``.

    grf = ground_reaction_from_model(model, state)
    grf.total.force, grf.total.cop, grf.feet["foot_l"].cop
"""

from __future__ import annotations

import functools
from typing import Any

from opensim_models.shared.parity._canonical import conformance
from opensim_models.tools.ground_reaction import (
    FOOT_SEGMENTS,
    ContactWrench,
    GroundReaction,
    Point2,
    Vec3,
    ground_reaction,
    half_space_wrench,
)

ENGINE = "opensim"


@functools.cache
def _standard() -> dict[str, Any]:
    return conformance.load_standard()


def _canonical(vec: Any) -> Vec3:
    """Rotate an OpenSim ``Vec3`` (or 3-sequence) into the canonical frame."""
    raw = (vec.get(0), vec.get(1), vec.get(2)) if hasattr(vec, "get") else vec
    return conformance.to_canonical(_standard(), ENGINE, raw)


def _sphere_forces(model: Any) -> list[Any]:
    import opensim

    forces = model.getForceSet()
    found = (
        opensim.SmoothSphereHalfSpaceForce.safeDownCast(forces.get(i))
        for i in range(forces.getSize())
    )
    return [force for force in found if force is not None]


def _contact_body(force: Any) -> str:
    """Name of the body that carries the force's contact sphere."""
    import opensim

    sphere = opensim.ContactGeometry.safeDownCast(force.getConnectee("sphere"))
    return str(sphere.getFrame().findBaseFrame().getName())


def contact_wrenches(model: Any, state: Any) -> list[ContactWrench]:
    """Canonical-frame wrench of every sphere/half-space contact force.

    Realizes *state* to the Dynamics stage.
    """
    model.realizeDynamics(state)
    out = []
    for force in _sphere_forces(model):
        labels, values = force.getRecordLabels(), force.getRecordValues(state)
        f, m = half_space_wrench(
            [labels.get(i) for i in range(labels.size())],
            [values.get(i) for i in range(values.size())],
        )
        out.append(ContactWrench(_contact_body(force), _canonical(f), _canonical(m)))
    return out


def ground_reaction_from_model(model: Any, state: Any) -> GroundReaction:
    """Per-foot and total GRF with CoP (canonical frame) for *model* at *state*.

    A foot clear of the ground reports a zero force and ``cop=None``; so does
    the total when neither foot is loaded.
    """
    return ground_reaction(contact_wrenches(model, state))


def foot_contact_points(model: Any, state: Any) -> dict[str, list[Point2]]:
    """Canonical ground-plane (x, y) of each foot sphere's lowest point, per foot.

    These are the vertices from which ``support_polygon`` builds the base.
    Realizes *state* to the Position stage.
    """
    import opensim

    model.realizePosition(state)
    points: dict[str, list[Point2]] = {foot: [] for foot in FOOT_SEGMENTS}
    for force in _sphere_forces(model):
        body = _contact_body(force)
        if body not in points:
            continue
        sphere = opensim.ContactSphere.safeDownCast(force.getConnectee("sphere"))
        centre = sphere.getFrame().findStationLocationInGround(
            state, sphere.get_location()
        )
        x, y, _ = _canonical(centre)
        points[body].append((x, y))
    return points
