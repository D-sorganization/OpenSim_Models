"""Optional segmental lumbar chain (L5/S1 .. L1/L2) for lift studies (#464).

Replaces the single 3-DOF ``lumbar`` CustomJoint with five CustomJoints (one
per lumbar level, caudal first) joined by four small link bodies. The default
model is untouched: the chain is built only when a ``LumbarCouplingLaw`` is
passed to ``create_full_body``.

Kinematics, with ``q`` one of the three driver coordinates (``lumbar_flex``,
``lumbar_lateral``, ``lumbar_rotate``), which keep their names and total
ranges so poses and limits written for the single joint still apply:

* level 0 (L5/S1) rotates by ``r_0 * q`` (a scaled TransformAxis),
* level ``i >= 1`` has its own coordinate constrained to ``r_i * q`` by a
  ``CoordinateCouplerConstraint``,

where ``r_i`` is the law's share of the total motion at level ``i`` and
``sum_i r_i = 1``. Each level applies its three rotations in the ``flex,
lateral, rotate`` order of the single joint, and the pelvis-to-torso rotation
is the caudal-first product of the level rotations. Cardan angles do not add,
so only motion about one axis sums to the driver angle.

Scope and limits of this first slice:

* the laws are *linear shares* of the total motion; per-level ratios from the
  literature ship with their own provenance (``source``) and are supplied by
  the caller. No published ratio is vendored here (cross-repo DRY: the shared
  package that owns them does not exist yet).
* levels are co-located (zero inter-level offsets) and carry no neutral
  lordosis, so the neutral pose equals the default model.
* link bodies carry a negligible regularising mass, not an anatomical one.
"""

from __future__ import annotations

import logging
import math
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from opensim_models.shared.contracts.preconditions import require_positive
from opensim_models.shared.parity.standard import JOINT_LIMITS
from opensim_models.shared.utils.constraint_helpers import add_coordinate_coupler
from opensim_models.shared.utils.xml_helpers import add_body, add_custom_joint

logger = logging.getLogger(__name__)

__all__ = [
    "LUMBAR_LEVELS",
    "LUMBAR_MOTIONS",
    "LumbarCouplingLaw",
    "add_lumbar_chain",
    "add_lumbar_chain_bodies",
    "uniform_lumbar_law",
]

#: Lumbar levels, caudal first (ADR-0055 composition order).
LUMBAR_LEVELS: tuple[str, ...] = ("L5_S1", "L4_L5", "L3_L4", "L2_L3", "L1_L2")

#: Motion key -> rotation axis, in the order the single joint applies them.
LUMBAR_MOTIONS: dict[str, str] = {
    "flex": "0 0 -1",
    "lateral": "-1 0 0",
    "rotate": "0 1 0",
}

# Link bodies between pelvis and torso, caudal first (L5 .. L2 vertebrae).
_LINK_BODIES: tuple[str, ...] = ("lumbar_L5", "lumbar_L4", "lumbar_L3", "lumbar_L2")
_BODY_CHAIN: tuple[str, ...] = ("pelvis", *_LINK_BODIES, "torso")
# Regularising link properties (not anatomical): keeps the mass matrix regular.
_LINK_MASS_KG = 0.01
_LINK_INERTIA_KGM2 = 1e-5
_SUM_TOL = 1e-9


def _require_text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _driver(motion: str) -> str:
    """Name of the driver coordinate (the total motion) for *motion*."""
    return f"lumbar_{motion}"


@dataclass(frozen=True)
class LumbarCouplingLaw:
    """Per-level shares of total lumbar motion, with provenance.

    ``ratios`` maps each motion in ``LUMBAR_MOTIONS`` to five shares, caudal
    first (``LUMBAR_LEVELS``). Each share must be positive and finite, and each
    motion's shares must sum to 1 within 1e-9, so the total range of motion is
    preserved. ``source`` is the citation of the published data, or an explicit
    statement that the law is not published; it is recorded in the model.
    """

    law_id: str
    version: str
    source: str
    ratios: Mapping[str, Sequence[float]]

    def __post_init__(self) -> None:
        _require_text(self.law_id, "law_id")
        _require_text(self.version, "version")
        _require_text(self.source, "source")
        checked: dict[str, tuple[float, ...]] = {}
        for motion in LUMBAR_MOTIONS:
            if motion not in self.ratios:
                raise ValueError(f"ratios is missing motion '{motion}'")
            shares = tuple(float(r) for r in self.ratios[motion])
            if len(shares) != len(LUMBAR_LEVELS):
                raise ValueError(
                    f"ratios['{motion}'] needs {len(LUMBAR_LEVELS)} levels, "
                    f"got {len(shares)}"
                )
            for level, share in zip(LUMBAR_LEVELS, shares, strict=True):
                require_positive(share, f"ratios['{motion}'][{level}]")
            if abs(math.fsum(shares) - 1.0) > _SUM_TOL:
                raise ValueError(
                    f"ratios['{motion}'] must sum to 1, got {math.fsum(shares)}"
                )
            checked[motion] = shares
        object.__setattr__(self, "ratios", checked)

    @property
    def provenance(self) -> str:
        """One-line record of the law in force, written to the model."""
        return f"Lumbar coupling law {self.law_id} v{self.version}: {self.source}"


def uniform_lumbar_law() -> LumbarCouplingLaw:
    """Equal share per level for every motion; explicitly not a published law."""
    equal = (1.0 / len(LUMBAR_LEVELS),) * len(LUMBAR_LEVELS)
    return LumbarCouplingLaw(
        law_id="uniform",
        version="1",
        source="equal partition over the five levels; not a published law",
        ratios=dict.fromkeys(LUMBAR_MOTIONS, equal),
    )


def add_lumbar_chain_bodies(bodyset: ET.Element, bodies: dict[str, ET.Element]) -> None:
    """Add the four link bodies (L5 .. L2) between pelvis and torso."""
    for name in _LINK_BODIES:
        bodies[name] = add_body(
            bodyset,
            name=name,
            mass=_LINK_MASS_KG,
            mass_center=(0, 0, 0),
            inertia_xx=_LINK_INERTIA_KGM2,
            inertia_yy=_LINK_INERTIA_KGM2,
            inertia_zz=_LINK_INERTIA_KGM2,
        )


def _level_coordinates(
    law: LumbarCouplingLaw, index: int, level: str
) -> list[dict[str, float | str]]:
    """Coordinate specs of one level (driver coordinates at level 0)."""
    coords: list[dict[str, float | str]] = []
    for motion, axis in LUMBAR_MOTIONS.items():
        low, high = JOINT_LIMITS[_driver(motion)]
        ratio = law.ratios[motion][index]
        coord: dict[str, float | str] = {"default_value": 0.0, "axis": axis}
        if index == 0:
            # The driver carries the total motion; the joint angle is ratio * q.
            coord.update(
                name=_driver(motion), range_min=low, range_max=high, scale=ratio
            )
        else:
            coord.update(
                name=f"{_driver(motion)}_{level}",
                range_min=ratio * low,
                range_max=ratio * high,
            )
        coords.append(coord)
    return coords


def add_lumbar_chain(
    jointset: ET.Element,
    constraintset: ET.Element,
    p_len: float,
    law: LumbarCouplingLaw,
) -> None:
    """Add the five level joints and their coupler constraints.

    Preconditions: link bodies exist (``add_lumbar_chain_bodies``); ``p_len``
    is positive. Postcondition: five CustomJoints ``lumbar_<level>`` chain
    pelvis to torso, the torso neutral placement equals the single joint's, and
    twelve couplers tie the lower levels' coordinates to the three drivers.
    """
    require_positive(p_len, "p_len")
    for index, level in enumerate(LUMBAR_LEVELS):
        add_custom_joint(
            jointset,
            name=f"lumbar_{level}",
            parent_body=_BODY_CHAIN[index],
            child_body=_BODY_CHAIN[index + 1],
            location_in_parent=(0, p_len / 2.0 if index == 0 else 0.0, 0),
            location_in_child=(0, 0, 0),
            coordinates=_level_coordinates(law, index, level),
        )
        if index == 0:
            continue
        for motion in LUMBAR_MOTIONS:
            add_coordinate_coupler(
                constraintset,
                name=f"{_driver(motion)}_{level}_coupler",
                independent=_driver(motion),
                dependent=f"{_driver(motion)}_{level}",
                slope=law.ratios[motion][index],
            )
    logger.info("Lumbar chain added using %s", law.provenance)
