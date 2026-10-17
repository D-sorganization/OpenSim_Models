"""Contact policy shared by every exercise model (OpenSim_Models#472).

The OpenSim counterpart of MuJoCo_Models ``exercises/contact_policy.py`` and
Pinocchio_Models ``shared/contact``. Everything the parity standard defines is
read from the vendored bundle; nothing is re-typed here:

* ``GROUND_FRICTION`` -- ``contact.ground_friction``. OpenSim's
  ``SmoothSphereHalfSpaceForce`` takes both coefficients, so both are used.
* The foot contact footprint -- ``contact.foot_box_m`` (length x width),
  centred on mid-foot, which ``pose_frame.ankle_x_m`` places ahead of the
  ankle. One contact sphere sits under each corner of the box.

Self-collision policy: an OpenSim model only has the contacts it declares, and
the packs declare foot-sphere / ground-half-space pairs only, so no body pair
can collide and no exclusion list is needed (MuJoCo needs ``<exclude>`` pairs).

The remaining constants are OpenSim contact-law parameters with no parity
counterpart. :func:`static_normal_force` is the engine's smoothed Hertz law
(Simbody ``SmoothSphereHalfSpaceForceImpl::calcForce``) at zero velocity, used
to seat the feet without loading OpenSim; ``tests/parity`` checks it against the
engine.
"""

from __future__ import annotations

import math
from typing import Final

from opensim_models.shared.contracts.preconditions import require_positive
from opensim_models.shared.parity.standard import (
    FOOT_CONTACT_DIMS,
    GROUND_FRICTION,
    STANDARD,
    STANDARD_HEIGHT,
)

__all__ = [
    "CONSTANT_CONTACT_FORCE",
    "CONTACT_DISSIPATION",
    "CONTACT_STIFFNESS",
    "FOOT_CONTACT_POINTS",
    "FOOT_SPHERE_RADIUS",
    "GROUND_FRICTION",
    "HERTZ_SMOOTHING",
    "VISCOUS_FRICTION",
    "foot_contact_offsets",
    "foot_sphere_names",
    "static_normal_force",
]

FOOT_SPHERE_RADIUS: Final = 0.02  # m
CONTACT_STIFFNESS: Final = 1.0e7  # Pa, Hertz modulus of the sphere/ground pair
CONTACT_DISSIPATION: Final = 0.5  # s/m, Hunt-Crossley
VISCOUS_FRICTION: Final = 0.2  # s/m
# Smoothing of the Hertz law: OpenSim's defaults, written into every model so
# the law below and the engine use the same values.
CONSTANT_CONTACT_FORCE: Final = 1.0e-5  # m^2 (``cf``: indentation^2 offset)
HERTZ_SMOOTHING: Final = 300.0  # 1/m (``bd``)

FOOT_CONTACT_POINTS: Final = (
    "heel_medial",
    "heel_lateral",
    "toe_medial",
    "toe_lateral",
)
_SIDES: Final = ("l", "r")
_ANKLE_X_M: Final = float(STANDARD["pose_frame"]["ankle_x_m"])


def foot_sphere_names() -> list[str]:
    """Contact-sphere names, left foot then right, in ``FOOT_CONTACT_POINTS`` order."""
    return [f"foot_{side}_{point}" for side in _SIDES for point in FOOT_CONTACT_POINTS]


def foot_contact_offsets(side: str, height_m: float) -> dict[str, tuple[float, float]]:
    """``(x, z)`` of each sphere centre in the *side* foot frame (OpenSim axes).

    The corners of the standard foot box, centred at mid-foot. Mid-foot is
    ``-ankle_x_m`` ahead of the ankle at the standard height and scales with
    *height_m*; the box itself does not scale. +X is forward and the right
    foot's lateral side is +Z.

    Raises:
        ValueError: *side* is not ``"l"``/``"r"`` or *height_m* is not positive.
    """
    if side not in _SIDES:
        raise ValueError(f"side must be one of {_SIDES}, got {side!r}")
    require_positive(height_m, "height_m")
    centre_x = -_ANKLE_X_M * height_m / STANDARD_HEIGHT
    half_len = 0.5 * FOOT_CONTACT_DIMS["length"]
    lateral = 0.5 * FOOT_CONTACT_DIMS["width"] * (1.0 if side == "r" else -1.0)
    return {
        "heel_medial": (centre_x - half_len, -lateral),
        "heel_lateral": (centre_x - half_len, lateral),
        "toe_medial": (centre_x + half_len, -lateral),
        "toe_lateral": (centre_x + half_len, lateral),
    }


def static_normal_force(
    indentation: float,
    *,
    radius: float = FOOT_SPHERE_RADIUS,
    stiffness: float = CONTACT_STIFFNESS,
) -> float:
    """Normal force (N) of one sphere at rest *indentation* metres into the ground.

    Simbody's smoothed Hertz law with zero normal velocity::

        k = stiffness^(2/3) / 2
        f = 4/3 k sqrt(R k) (d^2 + cf)^(3/4) (1 + tanh(bd d)) / 2

    The Hunt-Crossley factor is 1 at rest. Negative *indentation* (clear of
    the ground) still gives the law's small smoothing force.

    Postcondition: the result is finite and strictly positive, and increases
    with *indentation*.
    """
    require_positive(radius, "radius")
    require_positive(stiffness, "stiffness")
    if not math.isfinite(indentation):
        raise ValueError(f"indentation must be finite, got {indentation!r}")
    k = 0.5 * stiffness ** (2.0 / 3.0)
    hertz = (
        (4.0 / 3.0)
        * k
        * math.sqrt(radius * k)
        * (indentation * indentation + CONSTANT_CONTACT_FORCE) ** 0.75
    )
    return hertz * 0.5 * (1.0 + math.tanh(HERTZ_SMOOTHING * indentation))
