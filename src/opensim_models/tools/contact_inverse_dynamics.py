"""Inverse dynamics that reports the foot-contact load and the root residual.

OpenSim_Models#472, the port of MuJoCo_Models ``inverse_dynamics_with_contacts``
(MuJoCo_Models#453 / PR #482). ``InverseDynamicsSolver`` returns the
generalized forces needed *in addition to* every applied force, so with the
feet seated (``shared/body/foot_seating.py``) the contact forces are counted
and the pelvis FreeJoint entries are the load the contacts do not explain --
the residual ("hand of God") force. Excluding the contacts instead would put
the whole weight on the free joint, the silent misattribution MuJoCo#453 fixed.

The contact share is the difference between inverse dynamics with the foot
contact forces disabled and with them applied, at the same state and udot.

    report = inverse_dynamics_with_contacts(model, state)
    report.root_residual, report.root_contact, report.contact_count
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from opensim_models.shared.parity.via_poses import ROOT_COORDINATES
from opensim_models.tools.ground_reaction_opensim import _sphere_forces

__all__ = ["ContactInverseDynamics", "inverse_dynamics_with_contacts"]


@dataclass(frozen=True)
class ContactInverseDynamics:
    """Inverse dynamics split into the contact load and the remainder.

    Attributes:
        coordinates: Coordinate names in multibody-tree (mobility) order.
        generalized_forces: ``InverseDynamicsSolver`` output with every force
            applied: joint torques, and on the pelvis root the residual.
        contact_forces: Generalized force of the sphere/half-space contacts.
        contact_count: Contact spheres penetrating their half-space.
    """

    coordinates: tuple[str, ...]
    generalized_forces: np.ndarray
    contact_forces: np.ndarray
    contact_count: int

    def _root(self, values: np.ndarray) -> np.ndarray:
        index = {name: i for i, name in enumerate(self.coordinates)}
        return np.array([values[index[name]] for name in ROOT_COORDINATES])

    @property
    def root_residual(self) -> np.ndarray:
        """Pelvis (rx ry rz tx ty tz) load the contacts do not explain."""
        return self._root(self.generalized_forces)

    @property
    def root_contact(self) -> np.ndarray:
        """Pelvis (rx ry rz tx ty tz) load the contacts carry."""
        return self._root(self.contact_forces)


def _penetrates(force: Any, state: Any) -> bool:
    """True when the force's sphere dips below the y = 0 ground half-space."""
    import opensim

    sphere = opensim.ContactSphere.safeDownCast(force.getConnectee("sphere"))
    centre = sphere.getFrame().findStationLocationInGround(state, sphere.get_location())
    return bool(centre.get(1) < sphere.getRadius())


def _coordinate_order(model: Any) -> tuple[str, ...]:
    names = model.getCoordinateNamesInMultibodyTreeOrder()
    return tuple(str(names.getElt(i)) for i in range(names.size()))


def _solve(model: Any, state: Any, udot: np.ndarray) -> np.ndarray:
    import opensim

    tau = opensim.InverseDynamicsSolver(model).solve(state, opensim.Vector(udot))
    return np.array([tau.get(i) for i in range(tau.size())])


def _forward_udot(model: Any, state: Any) -> np.ndarray:
    model.realizeAcceleration(state)
    udot = state.getUDot()
    return np.array([udot.get(i) for i in range(udot.size())])


def inverse_dynamics_with_contacts(
    model: Any, state: Any, udot: np.ndarray | None = None
) -> ContactInverseDynamics:
    """Inverse dynamics at *state* with the foot contacts reported explicitly.

    Args:
        model: An initialized ``opensim.Model`` with a FreeJoint pelvis root.
        state: Its state (positions and speeds are used; not modified).
        udot: Generalized accelerations; ``None`` uses the forward-dynamics
            accelerations of *state*, at which the root residual vanishes.

    Postcondition: ``generalized_forces + contact_forces`` equals inverse
    dynamics with the contact forces removed.

    Raises:
        ValueError: the model has no free pelvis root, or *udot* has the
            wrong length or non-finite entries.
    """
    coordinates = _coordinate_order(model)
    if not set(ROOT_COORDINATES) <= set(coordinates):
        raise ValueError("contact inverse dynamics needs a free pelvis root")
    import opensim

    work = opensim.State(state)
    accel = _forward_udot(model, work) if udot is None else np.asarray(udot, float)
    if accel.shape != (work.getNU(),) or not np.all(np.isfinite(accel)):
        raise ValueError(f"udot must be {work.getNU()} finite values")
    contacts = _sphere_forces(model)
    model.realizePosition(work)
    count = sum(_penetrates(force, work) for force in contacts)
    applied = _solve(model, work, accel)
    for force in contacts:
        force.setAppliesForce(work, False)
    bare = _solve(model, work, accel)
    return ContactInverseDynamics(
        coordinates=coordinates,
        generalized_forces=applied,
        contact_forces=bare - applied,
        contact_count=count,
    )
