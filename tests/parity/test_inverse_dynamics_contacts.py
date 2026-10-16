"""Real OpenSim: gait inverse dynamics with active foot contacts (#472).

Port of MuJoCo_Models ``tests/parity/test_inverse_dynamics_contacts.py``
(MuJoCo_Models#453 / PR #482). With the soles seated at the contact
equilibrium the foot contacts are active, so ``InverseDynamicsSolver`` counts
their force and the pelvis (unactuated FreeJoint) entries are the load the
contacts do *not* explain -- the root residual.

Thresholds are MuJoCo's for the same input (the start state, zero velocity):

* ``IDENTITY_ATOL`` = 1e-9 N (N m on rotations): at the forward-dynamics
  acceleration the root residual vanishes once the contacts are counted.
  MuJoCo measured 9.0e-13 N; OpenSim 4.6 measures 3.7e-13.
* ``STATIC_RTOL`` = 1e-3 of the weight: with zero acceleration the vertical
  root residual plus the contact load is m g (MuJoCo's unchanged
  ``rel=1e-3``). Here the seated contacts carry the weight, so the residual
  itself is held to that bound: MuJoCo leaves -5.78 N (0.74 % W) on its root,
  OpenSim seats to the engine's own law and leaves 0.076 N (1e-4 W).
  MuJoCo's static check is vertical only; OpenSim's static rotational
  residuals (70 N m on pelvis_rx, -55 N m on pelvis_rz) are the single-stance
  pose's centre of mass off the stance foot and are not asserted.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.shared.body.foot_seating import supported_weight

try:
    import opensim
except ImportError:
    opensim = None

needs_opensim = pytest.mark.skipif(
    opensim is None,
    reason="opensim is not installed in this Python environment",
)

IDENTITY_ATOL = 1.0e-9
STATIC_RTOL = 1.0e-3
PELVIS_TY = 4  # index of pelvis_ty in the root coordinates (rx ry rz tx ty tz)


def _gait(tmp_path: Path):  # type: ignore[no-untyped-def]
    xml = EXERCISE_BUILDERS["gait"]()
    path = tmp_path / "gait.osim"
    path.write_text(xml, encoding="utf-8")
    model = opensim.Model(str(path))
    tree = ET.fromstring(xml).find("Model")
    assert tree is not None
    return model, model.initSystem(), supported_weight(tree)


@needs_opensim
def test_root_residual_vanishes_once_contacts_are_counted(tmp_path: Path) -> None:
    from opensim_models.tools.contact_inverse_dynamics import (
        inverse_dynamics_with_contacts,
    )

    model, state, weight = _gait(tmp_path)
    report = inverse_dynamics_with_contacts(model, state)
    assert report.contact_count == 4, "the seated stance foot must be in contact"
    assert report.root_contact[PELVIS_TY] > 0.5 * weight, "contacts carry the body"
    np.testing.assert_allclose(report.root_residual, 0.0, atol=IDENTITY_ATOL)


@needs_opensim
def test_static_root_residual_is_within_mujoco_bound(tmp_path: Path) -> None:
    from opensim_models.tools.contact_inverse_dynamics import (
        inverse_dynamics_with_contacts,
    )

    model, state, weight = _gait(tmp_path)
    report = inverse_dynamics_with_contacts(model, state, udot=np.zeros(34))
    vertical = report.root_residual[PELVIS_TY]
    assert vertical + report.root_contact[PELVIS_TY] == pytest.approx(
        weight, rel=STATIC_RTOL
    )
    assert abs(vertical) < STATIC_RTOL * weight


@needs_opensim
def test_contact_and_residual_close_the_equations_of_motion(tmp_path: Path) -> None:
    """Residual + contact equals inverse dynamics with the contacts removed."""
    from opensim_models.tools.contact_inverse_dynamics import (
        inverse_dynamics_with_contacts,
    )

    model, state, _ = _gait(tmp_path)
    udot = np.zeros(state.getNU())
    report = inverse_dynamics_with_contacts(model, state, udot=udot)
    for i in range(model.getForceSet().getSize()):
        model.getForceSet().get(i).setAppliesForce(state, False)
    bare = opensim.InverseDynamicsSolver(model).solve(state, opensim.Vector(udot))
    expected = np.array([bare.get(i) for i in range(bare.size())])
    np.testing.assert_allclose(
        report.generalized_forces + report.contact_forces,
        expected,
        atol=IDENTITY_ATOL,
    )


@needs_opensim
def test_fixed_root_model_is_rejected(tmp_path: Path) -> None:
    from opensim_models.tools.contact_inverse_dynamics import (
        inverse_dynamics_with_contacts,
    )

    path = tmp_path / "bench.osim"
    path.write_text(EXERCISE_BUILDERS["bench_press"](), encoding="utf-8")
    model = opensim.Model(str(path))
    with pytest.raises(ValueError, match="free"):
        inverse_dynamics_with_contacts(model, model.initSystem())
