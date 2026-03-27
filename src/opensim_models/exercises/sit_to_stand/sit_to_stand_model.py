"""Sit-to-stand model builder.

Builds an OpenSim model configured for sit-to-stand motion analysis.
Adds a chair body as a fixed environmental constraint and sets the
initial pose to a seated position. No barbell is attached.

Biomechanical notes:
- Primary movers: quadriceps, gluteus maximus, hamstrings, erector spinae
- The model captures the transition from seated to standing
- Chair seat height is configurable (default 0.45 m)
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from opensim_models.exercises.base import ExerciseConfig, ExerciseModelBuilder
from opensim_models.shared.utils.xml_helpers import (
    add_weld_joint,
    set_coordinate_default,
)

# Default chair seat height in meters
_DEFAULT_SEAT_HEIGHT = 0.45


class SitToStandModelBuilder(ExerciseModelBuilder):
    """Builds a sit-to-stand OpenSim model.

    Adds a chair body welded to ground and sets the initial pose
    to a seated position with ~90 deg hip and knee flexion.
    """

    def __init__(
        self,
        config: ExerciseConfig | None = None,
        seat_height: float = _DEFAULT_SEAT_HEIGHT,
    ) -> None:
        super().__init__(config)
        self.seat_height = seat_height

    @property
    def exercise_name(self) -> str:
        return "sit_to_stand"

    def _pre_attach_hook(self, bodyset: ET.Element, jointset: ET.Element) -> None:
        """Add a chair body welded to ground."""
        chair = ET.SubElement(bodyset, "Body", name="chair")
        ET.SubElement(chair, "mass").text = "10.0"
        ET.SubElement(chair, "mass_center").text = "0 0 0"
        ET.SubElement(chair, "inertia").text = "0.1 0.1 0.1 0 0 0"

        add_weld_joint(
            jointset,
            name="chair_to_ground",
            parent_body="ground",
            child_body="chair",
            location_in_parent=(0, self.seat_height, -0.3),
            location_in_child=(0, 0, 0),
        )

    def attach_barbell(
        self,
        jointset: ET.Element,
        body_bodies: dict[str, ET.Element],
        barbell_bodies: dict[str, ET.Element],
    ) -> None:
        """No-op: sit-to-stand does not use a barbell."""

    def set_initial_pose(self, jointset: ET.Element) -> None:
        """Set seated initial pose: ~90 deg hip and knee flexion.

        Arms hang naturally at the sides.
        """
        hip_flex = 1.5708  # ~90 degrees
        knee_flex = -1.5708  # ~90 degrees
        for side in ("l", "r"):
            set_coordinate_default(jointset, f"hip_{side}_flex", hip_flex)
            set_coordinate_default(jointset, f"hip_{side}_adduct", 0.0)
            set_coordinate_default(jointset, f"hip_{side}_rotate", 0.0)
            set_coordinate_default(jointset, f"knee_{side}_flex", knee_flex)
            set_coordinate_default(jointset, f"ankle_{side}_flex", 0.1745)  # ~10 deg
            set_coordinate_default(jointset, f"ankle_{side}_inversion", 0.0)


def build_sit_to_stand_model(
    body_mass: float = 80.0,
    height: float = 1.75,
    seat_height: float = _DEFAULT_SEAT_HEIGHT,
) -> str:
    """Convenience function to build a sit-to-stand model XML string.

    Default: 80 kg person, 1.75 m tall, 0.45 m seat height, no barbell.
    """
    from opensim_models.shared.barbell import BarbellSpec
    from opensim_models.shared.body import BodyModelSpec

    config = ExerciseConfig(
        body_spec=BodyModelSpec(total_mass=body_mass, height=height),
        barbell_spec=BarbellSpec.mens_olympic(plate_mass_per_side=0.0),
    )
    return SitToStandModelBuilder(config, seat_height=seat_height).build()
