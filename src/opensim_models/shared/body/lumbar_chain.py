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

Each level's range is ``r_i`` times the driver range. For a law built from
measured per-level ranges of motion (``LumbarCouplingLaw.from_level_rom``),
``r_i`` is the level's share of the summed range, so the level limits are
the cited per-level ranges scaled by one factor per motion
(``lumbar_coupling_data`` ships a cited law).

Mass: the links are carved from the torso (``add_lumbar_chain_bodies``).
Limits: levels are co-located (zero inter-level offsets) with no neutral
lordosis, so the neutral pose equals the default model; laws are linear,
positive shares (no cross-axis coupling).
"""

from __future__ import annotations

import logging
import math
import re
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from opensim_models.shared.contracts.preconditions import require_positive
from opensim_models.shared.parity.standard import JOINT_LIMITS
from opensim_models.shared.utils.constraint_helpers import add_coordinate_coupler
from opensim_models.shared.utils.xml_helpers import (
    add_body,
    add_custom_joint,
    body_inertial,
    scale_body_inertial,
)

logger = logging.getLogger(__name__)

__all__ = [
    "LUMBAR_LEVELS",
    "LUMBAR_MOTIONS",
    "LumbarCouplingLaw",
    "add_lumbar_chain",
    "add_lumbar_chain_bodies",
    "require_lumbar_law",
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
# Regularising link mass carved from the torso (not an anatomical value).
_LINK_MASS_KG = 0.01
_SUM_TOL = 1e-9
_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")


def _require_text(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _driver(motion: str) -> str:
    """Name of the driver coordinate (the total motion) for *motion*."""
    return f"lumbar_{motion}"


def _per_level(
    table: Mapping[str, Sequence[float]], name: str
) -> dict[str, tuple[float, ...]]:
    """Validate a motion -> five positive finite values table (caudal first)."""
    checked: dict[str, tuple[float, ...]] = {}
    for motion in LUMBAR_MOTIONS:
        if motion not in table:
            raise ValueError(f"{name} is missing motion '{motion}'")
        values = tuple(float(v) for v in table[motion])
        if len(values) != len(LUMBAR_LEVELS):
            raise ValueError(
                f"{name}['{motion}'] needs {len(LUMBAR_LEVELS)} levels, "
                f"got {len(values)}"
            )
        for level, value in zip(LUMBAR_LEVELS, values, strict=True):
            require_positive(value, f"{name}['{motion}'][{level}]")
        checked[motion] = values
    return checked


@dataclass(frozen=True)
class LumbarCouplingLaw:
    """Per-level shares of total lumbar motion, with provenance.

    ``ratios`` maps each motion in ``LUMBAR_MOTIONS`` to five shares, caudal
    first (``LUMBAR_LEVELS``). Each share must be positive and finite, and each
    motion's shares must sum to 1 within 1e-9, so the total range of motion is
    preserved. ``source`` is the citation of the published data, or an explicit
    statement that the law is not published; it is recorded in the model.

    ``level_rom_deg`` (optional) holds the measured per-level ranges of motion
    the shares were derived from; the shares must then be proportional to it.
    ``doi`` (optional) is the bare DOI of the source, e.g. ``10.1000/xyz``.
    """

    law_id: str
    version: str
    source: str
    ratios: Mapping[str, Sequence[float]]
    level_rom_deg: Mapping[str, Sequence[float]] | None = None
    doi: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.law_id, "law_id")
        _require_text(self.version, "version")
        _require_text(self.source, "source")
        if self.doi is not None and not _DOI_RE.match(self.doi):
            raise ValueError(f"doi must be a bare DOI like 10.1000/x, got {self.doi!r}")
        ratios = _per_level(self.ratios, "ratios")
        for motion, shares in ratios.items():
            if abs(math.fsum(shares) - 1.0) > _SUM_TOL:
                raise ValueError(
                    f"ratios['{motion}'] must sum to 1, got {math.fsum(shares)}"
                )
        object.__setattr__(self, "ratios", ratios)
        if self.level_rom_deg is not None:
            rom = _per_level(self.level_rom_deg, "level_rom_deg")
            for motion, values in rom.items():
                total = math.fsum(values)
                for share, value in zip(ratios[motion], values, strict=True):
                    if abs(share - value / total) > _SUM_TOL:
                        raise ValueError(
                            f"ratios['{motion}'] must be proportional to level_rom_deg"
                        )
            object.__setattr__(self, "level_rom_deg", rom)

    @classmethod
    def from_level_rom(
        cls,
        law_id: str,
        version: str,
        source: str,
        level_rom_deg: Mapping[str, Sequence[float]],
        *,
        doi: str | None = None,
    ) -> LumbarCouplingLaw:
        """Law whose shares are each level's fraction of the summed range.

        Assumes motion is distributed across levels in proportion to each
        level's measured range of motion (a modelling assumption).
        """
        rom = _per_level(level_rom_deg, "level_rom_deg")
        ratios = {
            m: tuple(v / math.fsum(vals) for v in vals) for m, vals in rom.items()
        }
        return cls(law_id, version, source, ratios, level_rom_deg=rom, doi=doi)

    @property
    def provenance(self) -> str:
        """One-line record of the law in force, written to the model."""
        doi = f" (doi:{self.doi})" if self.doi else ""
        return f"Lumbar coupling law {self.law_id} v{self.version}: {self.source}{doi}"


def require_lumbar_law(law: object) -> None:
    """Precondition: *law* is ``None`` or a ``LumbarCouplingLaw``."""
    if law is not None and not isinstance(law, LumbarCouplingLaw):
        raise TypeError(
            f"lumbar_chain must be a LumbarCouplingLaw or None, got {type(law).__name__}"
        )


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
    """Add the four link bodies (L5 .. L2), carving their mass from the torso.

    Precondition: ``bodies['torso']`` exists and outweighs the links.
    Each link takes a small regularising mass from the torso, with the torso's
    mass centre and a mass-proportional share of its central inertia. As all
    frames coincide in the neutral pose, torso plus links keep the lumped
    torso's mass, mass centre and inertia (postcondition, up to XML rounding).
    """
    torso = bodies["torso"]
    mass, mass_center, inertia = body_inertial(torso)
    carved = _LINK_MASS_KG * len(_LINK_BODIES)
    require_positive(mass - carved, "torso mass left after carving the links")
    scale_body_inertial(torso, (mass - carved) / mass)
    share = _LINK_MASS_KG / mass
    xx, yy, zz, xy, xz, yz = (share * v for v in inertia)
    for name in _LINK_BODIES:
        bodies[name] = add_body(
            bodyset,
            name=name,
            mass=_LINK_MASS_KG,
            mass_center=mass_center,
            inertia_xx=xx,
            inertia_yy=yy,
            inertia_zz=zz,
            inertia_xy=xy,
            inertia_xz=xz,
            inertia_yz=yz,
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

    Preconditions: ``law`` is a ``LumbarCouplingLaw``; link bodies exist
    (``add_lumbar_chain_bodies``); ``p_len`` is positive. Postcondition: five
    CustomJoints ``lumbar_<level>`` chain pelvis to torso, the torso neutral
    placement equals the single joint's, and twelve couplers tie the lower
    levels' coordinates to the three drivers.
    """
    require_lumbar_law(law)
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
