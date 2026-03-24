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
    cylinder_inertia,
    hollow_cylinder_inertia,
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
    """
    logger.info("Creating barbell: %.1f kg total", spec.total_mass)
    shaft_inertia = cylinder_inertia(
        spec.shaft_mass, spec.shaft_radius, spec.shaft_length
    )

    # Compute inertia for bare sleeve
    sleeve_inertia = hollow_cylinder_inertia(
        spec.sleeve_mass,
        inner_radius=spec.sleeve_inner_radius,
        outer_radius=spec.sleeve_radius,
        length=spec.sleeve_length,
    )

    if spec.plate_mass_per_side > 0:
        # Standard plate radius is 0.225m (450mm diameter)
        plate_inertia = hollow_cylinder_inertia(
            spec.plate_mass_per_side,
            inner_radius=spec.sleeve_radius,
            outer_radius=0.225,
            length=max(0.01, spec.plate_mass_per_side * 0.002), # approximate plate thickness
        )
        sleeve_inertia = (
            sleeve_inertia[0] + plate_inertia[0],
            sleeve_inertia[1] + plate_inertia[1],
            sleeve_inertia[2] + plate_inertia[2],
        )

    sleeve_total_mass = spec.sleeve_mass + spec.plate_mass_per_side

    shaft_name = f"{prefix}_shaft"
    left_name = f"{prefix}_left_sleeve"
    right_name = f"{prefix}_right_sleeve"

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

    return {
        shaft_name: shaft_body,
        left_name: left_body,
        right_name: right_body,
    }
