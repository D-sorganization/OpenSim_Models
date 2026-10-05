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

import logging
import math
import xml.etree.ElementTree as ET

from opensim_models.exercises.base import ExerciseConfig, ExerciseModelBuilder
from opensim_models.shared.body._segment_data import _seg
from opensim_models.shared.body.ground_placement import (
    lowest_contact_height_below_pelvis,
)
from opensim_models.shared.utils.xml_helpers import (
    add_weld_joint,
    set_coordinate_defaults,
)

logger = logging.getLogger(__name__)

# Default chair seat height in meters
_DEFAULT_SEAT_HEIGHT = 0.45
# Seated knee lift: extra hip flexion (shin kept vertical) that rests the feet
# on the floor, searched within +/-30 deg of the 90/90 sitting pose.
_KNEE_LIFT_LIMIT = math.radians(30.0)
_KNEE_LIFT_ITERATIONS = 40


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

    @property
    def uses_barbell(self) -> bool:
        return False

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
            location_in_parent=(-0.3, self.seat_height, 0),  # behind the pelvis
            location_in_child=(0, 0, 0),
        )

    def _initial_pelvis_height(self, model: ET.Element) -> float:
        """Seated start: the pelvis rests on the seat and the feet on the floor.

        Lifts the knees (hip flexion 90 deg + a, knee -(90 deg + a), so the
        shin stays vertical) until the lowest foot sphere touches y = 0 (#383).
        """
        _, pelvis_len, _ = _seg(self.body_spec, "pelvis")
        pelvis_ty = self.seat_height + pelvis_len / 2.0
        self._rest_feet_on_floor(model, pelvis_ty)
        return pelvis_ty

    def _rest_feet_on_floor(self, model: ET.Element, pelvis_ty: float) -> None:
        """Bisect the knee lift so the feet touch the floor (clamped if not)."""
        jointset = model.find("JointSet")
        if jointset is None:
            raise ValueError("model has no JointSet")

        def gap(lift: float) -> float:
            self._set_seated_legs(jointset, lift)
            return pelvis_ty + lowest_contact_height_below_pelvis(model)

        lo, hi = -_KNEE_LIFT_LIMIT, _KNEE_LIFT_LIMIT
        if gap(lo) > 0.0 or gap(hi) < 0.0:
            logger.warning(
                "Seat height %.3f m cannot rest the feet on the floor", self.seat_height
            )
            self._set_seated_legs(jointset, lo if gap(lo) > 0.0 else hi)
            return
        for _ in range(_KNEE_LIFT_ITERATIONS):
            mid = (lo + hi) / 2.0
            lo, hi = (mid, hi) if gap(mid) < 0.0 else (lo, mid)
        self._set_seated_legs(jointset, (lo + hi) / 2.0)

    @staticmethod
    def _set_seated_legs(jointset: ET.Element, lift: float) -> None:
        defaults = {}
        for side in ("l", "r"):
            defaults[f"hip_{side}_flex"] = math.pi / 2.0 + lift
            defaults[f"knee_{side}_flex"] = -(math.pi / 2.0 + lift)
        set_coordinate_defaults(jointset, defaults)

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
        defaults = {}
        for side in ("l", "r"):
            defaults[f"hip_{side}_flex"] = hip_flex
            defaults[f"hip_{side}_adduct"] = 0.0
            defaults[f"hip_{side}_rotate"] = 0.0
            defaults[f"knee_{side}_flex"] = knee_flex
            defaults[f"ankle_{side}_flex"] = 0.1745  # ~10 deg
            defaults[f"ankle_{side}_inversion"] = 0.0
        set_coordinate_defaults(jointset, defaults)


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
