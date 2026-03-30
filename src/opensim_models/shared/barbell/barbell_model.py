"""Olympic barbell model for OpenSim.

Standard Olympic barbell dimensions (IWF / IPF regulations):
- Men's bar: 2.20 m total length, 1.31 m between collars, 28 mm shaft
  diameter, 50 mm sleeve diameter, 20 kg unloaded.
- Women's bar: 2.01 m total length, 1.31 m between collars, 25 mm shaft
  diameter, 50 mm sleeve diameter, 15 kg unloaded.

The barbell is modelled as three rigid bodies (left_sleeve, shaft, right_sleeve)
connected by WeldJoints. Plates are added as additional mass on the sleeves.

Law of Demeter: callers interact only with BarbellSpec and create_barbell_bodies;
internal geometry details remain encapsulated.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from opensim_models.shared.contracts.preconditions import (
    require_non_negative,
    require_positive,
)
from opensim_models.shared.utils.geometry import (
    cylinder_inertia_along_x,
    hollow_cylinder_inertia_along_x,
)
from opensim_models.shared.utils.xml_helpers import (
    add_body,
    add_weld_joint,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BarbellSpec:
    """Immutable specification for a barbell.

    All lengths in meters, masses in kg, diameters in meters.
    """

    total_length: float = 2.20
    shaft_length: float = 1.31
    shaft_diameter: float = 0.028
    sleeve_diameter: float = 0.050
    bar_mass: float = 20.0
    plate_mass_per_side: float = 0.0
    sleeve_inner_radius: float = (
        0.014  # Inner bore radius: fits over 28 mm shaft (metres)
    )

    def __post_init__(self) -> None:
        require_positive(self.total_length, "total_length")
        require_positive(self.shaft_length, "shaft_length")
        require_positive(self.shaft_diameter, "shaft_diameter")
        require_positive(self.sleeve_diameter, "sleeve_diameter")
        require_positive(self.bar_mass, "bar_mass")
        require_non_negative(self.plate_mass_per_side, "plate_mass_per_side")
        require_positive(self.sleeve_inner_radius, "sleeve_inner_radius")
        if self.shaft_length >= self.total_length:
            raise ValueError(
                f"shaft_length ({self.shaft_length}) must be < "
                f"total_length ({self.total_length})"
            )
        if self.sleeve_inner_radius >= self.sleeve_radius:
            raise ValueError(
                f"sleeve_inner_radius ({self.sleeve_inner_radius}) must be < "
                f"sleeve_radius ({self.sleeve_radius})"
            )

    @property
    def sleeve_length(self) -> float:
        """Length of one sleeve (half of non-shaft portion)."""
        return (self.total_length - self.shaft_length) / 2.0

    @property
    def shaft_radius(self) -> float:
        return self.shaft_diameter / 2.0

    @property
    def sleeve_radius(self) -> float:
        return self.sleeve_diameter / 2.0

    @property
    def shaft_mass(self) -> float:
        """Mass attributed to the shaft (proportional to length)."""
        shaft_fraction = self.shaft_length / self.total_length
        return self.bar_mass * shaft_fraction

    @property
    def sleeve_mass(self) -> float:
        """Mass of one bare sleeve (no plates)."""
        sleeve_fraction = self.sleeve_length / self.total_length
        return self.bar_mass * sleeve_fraction

    @property
    def total_mass(self) -> float:
        """Total barbell mass including plates on both sides."""
        return self.bar_mass + 2.0 * self.plate_mass_per_side

    @classmethod
    def mens_olympic(cls, plate_mass_per_side: float = 0.0) -> BarbellSpec:
        """Standard men's Olympic barbell (20 kg, 2.20 m)."""
        return cls(plate_mass_per_side=plate_mass_per_side)

    @classmethod
    def womens_olympic(cls, plate_mass_per_side: float = 0.0) -> BarbellSpec:
        """Standard women's Olympic barbell (15 kg, 2.01 m)."""
        return cls(
            total_length=2.01,
            shaft_length=1.31,
            shaft_diameter=0.025,
            sleeve_diameter=0.050,
            bar_mass=15.0,
            plate_mass_per_side=plate_mass_per_side,
        )


def _compute_sleeve_inertia(
    spec: BarbellSpec,
) -> tuple[float, float, float]:
    """Compute the combined inertia tuple for one loaded sleeve.

    DRY helper: extracted from create_barbell_bodies to keep that function
    under the 80-line threshold.

    Returns:
        (Ixx, Iyy, Izz) for the sleeve including any loaded plates.
    """
    sleeve_inertia = hollow_cylinder_inertia_along_x(
        spec.sleeve_mass,
        inner_radius=spec.sleeve_inner_radius,
        outer_radius=spec.sleeve_radius,
        length=spec.sleeve_length,
    )
    if spec.plate_mass_per_side > 0:
        # Standard plate radius is 0.225 m (450 mm diameter)
        plate_inertia = hollow_cylinder_inertia_along_x(
            spec.plate_mass_per_side,
            inner_radius=spec.sleeve_radius,
            outer_radius=0.225,
            length=max(0.01, spec.plate_mass_per_side * 0.002),
        )
        sleeve_inertia = (
            sleeve_inertia[0] + plate_inertia[0],
            sleeve_inertia[1] + plate_inertia[1],
            sleeve_inertia[2] + plate_inertia[2],
        )
    return sleeve_inertia


def _add_barbell_bodies(
    bodyset: ET.Element,
    spec: BarbellSpec,
    shaft_name: str,
    left_name: str,
    right_name: str,
    sleeve_inertia: tuple[float, float, float],
) -> tuple[ET.Element, ET.Element, ET.Element]:
    """Add shaft and sleeve body elements to *bodyset*.

    DRY helper: extracted from create_barbell_bodies.

    Returns:
        (shaft_body, left_body, right_body) XML elements.
    """
    shaft_inertia = cylinder_inertia_along_x(
        spec.shaft_mass, spec.shaft_radius, spec.shaft_length
    )
    sleeve_total_mass = spec.sleeve_mass + spec.plate_mass_per_side

    shaft_body = add_body(
        bodyset,
        name=shaft_name,
        mass=spec.shaft_mass,
        mass_center=(0, 0, 0),
        inertia_xx=shaft_inertia[0],
        inertia_yy=shaft_inertia[1],
        inertia_zz=shaft_inertia[2],
    )
    left_body = add_body(
        bodyset,
        name=left_name,
        mass=sleeve_total_mass,
        mass_center=(0, 0, 0),
        inertia_xx=sleeve_inertia[0],
        inertia_yy=sleeve_inertia[1],
        inertia_zz=sleeve_inertia[2],
    )
    right_body = add_body(
        bodyset,
        name=right_name,
        mass=sleeve_total_mass,
        mass_center=(0, 0, 0),
        inertia_xx=sleeve_inertia[0],
        inertia_yy=sleeve_inertia[1],
        inertia_zz=sleeve_inertia[2],
    )
    return shaft_body, left_body, right_body


def _add_sleeve_weld_joints(
    jointset: ET.Element,
    spec: BarbellSpec,
    prefix: str,
    shaft_name: str,
    left_name: str,
    right_name: str,
) -> None:
    """Weld left and right sleeves to the shaft.

    DRY helper: extracted from create_barbell_bodies.
    """
    half_shaft = spec.shaft_length / 2.0
    half_sleeve = spec.sleeve_length / 2.0

    add_weld_joint(
        jointset,
        name=f"{prefix}_left_weld",
        parent_body=shaft_name,
        child_body=left_name,
        location_in_parent=(-half_shaft, 0, 0),
        location_in_child=(half_sleeve, 0, 0),
    )
    add_weld_joint(
        jointset,
        name=f"{prefix}_right_weld",
        parent_body=shaft_name,
        child_body=right_name,
        location_in_parent=(half_shaft, 0, 0),
        location_in_child=(-half_sleeve, 0, 0),
    )


def create_barbell_bodies(
    bodyset: ET.Element,
    jointset: ET.Element,
    spec: BarbellSpec,
    *,
    prefix: str = "barbell",
) -> dict[str, ET.Element]:
    """Add barbell bodies and joints to existing OpenSim body/joint sets.

    Returns dict of created body elements keyed by name.

    The barbell shaft center is at the local origin. Sleeves extend
    symmetrically along the X-axis (left = -X, right = +X).

    DbC preconditions are enforced by BarbellSpec.__post_init__.
    """
    require_positive(spec.total_mass, "spec.total_mass")
    logger.info("Creating barbell: %.1f kg total", spec.total_mass)

    shaft_name = f"{prefix}_shaft"
    left_name = f"{prefix}_left_sleeve"
    right_name = f"{prefix}_right_sleeve"

    sleeve_inertia = _compute_sleeve_inertia(spec)
    shaft_body, left_body, right_body = _add_barbell_bodies(
        bodyset, spec, shaft_name, left_name, right_name, sleeve_inertia
    )
    _add_sleeve_weld_joints(jointset, spec, prefix, shaft_name, left_name, right_name)

    return {
        shaft_name: shaft_body,
        left_name: left_body,
        right_name: right_body,
    }
