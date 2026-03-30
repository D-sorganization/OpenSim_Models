"""Base exercise model builder.

DRY: All five exercises share the same skeleton for creating an OpenSim
model XML — differing only in barbell attachment strategy, initial pose,
and joint coordinate defaults. This base class encapsulates the shared
workflow; subclasses override hooks to customize.

Law of Demeter: Exercise builders interact with BarbellSpec and BodyModelSpec
through their public APIs, never reaching into internal segment tables.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from opensim_models.exercises.constants import (
    _FLOOR_PULL_HIP_ANGLE,
    _FLOOR_PULL_KNEE_ANGLE,
    _FLOOR_PULL_LUMBAR_ANGLE,
)
from opensim_models.shared.barbell import BarbellSpec, create_barbell_bodies
from opensim_models.shared.body import (
    BodyModelSpec,
    add_foot_contact_spheres,
    create_full_body,
)
from opensim_models.shared.contracts.postconditions import (
    ensure_coordinates_within_bounds,
    ensure_valid_xml,
)
from opensim_models.shared.utils.contact_helpers import (
    add_contact_half_space,
    add_hunt_crossley_force,
)
from opensim_models.shared.utils.xml_helpers import (
    add_weld_joint,
    serialize_model,
    set_coordinate_default,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExerciseConfig:
    """Configuration common to all exercise models."""

    body_spec: BodyModelSpec = field(default_factory=BodyModelSpec)
    barbell_spec: BarbellSpec = field(default_factory=BarbellSpec.mens_olympic)
    gravity: tuple[float, float, float] = (0.0, -9.80665, 0.0)
    grip_offset: float = 0.40  # meters from shaft center to hand (half-width)


def set_floor_pull_initial_pose(jointset: ET.Element) -> None:
    """Set the shared floor-pull initial pose (deadlift, snatch, clean-and-jerk).

    DRY: extracted from three identical loops in deadlift, snatch, and
    clean_and_jerk set_initial_pose methods.
    """
    for side in ("l", "r"):
        set_coordinate_default(jointset, f"hip_{side}_flex", _FLOOR_PULL_HIP_ANGLE)
        set_coordinate_default(jointset, f"hip_{side}_adduct", 0.0)
        set_coordinate_default(jointset, f"hip_{side}_rotate", 0.0)
        set_coordinate_default(jointset, f"knee_{side}_flex", _FLOOR_PULL_KNEE_ANGLE)
    set_coordinate_default(jointset, "lumbar_flex", _FLOOR_PULL_LUMBAR_ANGLE)


def attach_barbell_to_hands(
    jointset: ET.Element,
    grip_offset: float,
) -> None:
    """Weld barbell shaft to both hands at the given grip offset.

    DRY: extracted from four identical attach_barbell implementations
    (deadlift, snatch, clean_and_jerk, bench_press).

    Args:
        jointset: XML JointSet element.
        grip_offset: distance from shaft center to each hand (metres).
    """
    add_weld_joint(
        jointset,
        name="barbell_to_left_hand",
        parent_body="hand_l",
        child_body="barbell_shaft",
        location_in_parent=(0, 0, 0),
        location_in_child=(-grip_offset, 0, 0),
    )
    add_weld_joint(
        jointset,
        name="barbell_to_right_hand",
        parent_body="hand_r",
        child_body="barbell_shaft",
        location_in_parent=(0, 0, 0),
        location_in_child=(grip_offset, 0, 0),
    )


class ExerciseModelBuilder(ABC):
    """Abstract builder for exercise-specific OpenSim models.

    Subclasses must implement:
      - exercise_name: str property
      - attach_barbell(): how the barbell connects to the body
      - set_initial_pose(): default coordinate values for the start position
    """

    def __init__(self, config: ExerciseConfig | None = None) -> None:
        self.config = config or ExerciseConfig()

    # --- LoD interface properties ---
    # Callers (including subclasses) should use these accessors rather than
    # reaching two levels deep into self.config.<field>.

    @property
    def body_spec(self) -> BodyModelSpec:
        """Body model specification (LoD: avoids self.config.body_spec)."""
        return self.config.body_spec

    @property
    def barbell_spec(self) -> BarbellSpec:
        """Barbell specification (LoD: avoids self.config.barbell_spec)."""
        return self.config.barbell_spec

    @property
    def gravity(self) -> tuple[float, float, float]:
        """Gravity vector (LoD: avoids self.config.gravity)."""
        return self.config.gravity

    @property
    def grip_offset(self) -> float:
        """Grip offset in metres (LoD: avoids self.config.grip_offset)."""
        return self.config.grip_offset

    @property
    @abstractmethod
    def exercise_name(self) -> str:
        """Human-readable exercise name used in the model XML."""

    @property
    def uses_barbell(self) -> bool:
        """Return True if this exercise uses a barbell.

        Override in subclasses (e.g. gait, sit-to-stand) that do not
        attach a barbell to the model.
        """
        return True

    @abstractmethod
    def attach_barbell(
        self,
        jointset: ET.Element,
        body_bodies: dict[str, ET.Element],
        barbell_bodies: dict[str, ET.Element],
    ) -> None:
        """Add joints connecting barbell to body (exercise-specific)."""

    @abstractmethod
    def set_initial_pose(self, jointset: ET.Element) -> None:
        """Set default coordinate values for the starting position."""

    def _pre_attach_hook(  # noqa: B027 -- intentional no-op hook, not a missing abstract
        self, bodyset: ET.Element, jointset: ET.Element
    ) -> None:
        """Hook called after bodies are built, before barbell is attached.

        Subclasses may override to inject additional bodies or joints
        (e.g. a bench body and constraint for bench press).
        The default implementation is a no-op.
        """

    def _skip_ground_joint(self) -> bool:
        """Return True if the pelvis-ground FreeJoint should be omitted.

        Override in subclasses that supply their own pelvis parent joint
        (e.g. bench press, where pelvis is welded to the bench body).
        """
        return False

    def _post_contact_hook(  # noqa: B027 -- intentional no-op hook, not a missing abstract
        self, model: ET.Element
    ) -> None:
        """Hook called after standard ground contact is added.

        Subclasses may override to inject additional contact surfaces
        (e.g. a bench contact surface for bench press).
        The default implementation is a no-op.
        """

    def build(self) -> str:
        """Build the complete OpenSim model XML and return as string.

        Postcondition: returned string is well-formed XML.
        """
        logger.info("Building %s model", self.exercise_name)
        root = ET.Element("OpenSimDocument", Version="40500")
        model = ET.SubElement(root, "Model", name=self.exercise_name)

        # Gravity
        gravity = ET.SubElement(model, "gravity")
        g = self.gravity
        gravity.text = f"{g[0]:.6f} {g[1]:.6f} {g[2]:.6f}"

        # Ground body
        ground_el = ET.SubElement(model, "Ground", name="ground")
        ET.SubElement(ground_el, "mass").text = "0"
        ET.SubElement(ground_el, "mass_center").text = "0 0 0"
        ET.SubElement(ground_el, "inertia").text = "0 0 0 0 0 0"

        bodyset = ET.SubElement(model, "BodySet")
        jointset = ET.SubElement(model, "JointSet")

        # Build body (skip the ground FreeJoint when subclass requests it)
        body_bodies = create_full_body(
            bodyset,
            jointset,
            self.body_spec,
            skip_ground_joint=self._skip_ground_joint(),
        )

        # Build barbell (only for exercises that use one)
        barbell_bodies: dict[str, ET.Element] = {}
        if self.uses_barbell:
            barbell_bodies = create_barbell_bodies(bodyset, jointset, self.barbell_spec)

        # Subclass hook: inject extra bodies/joints before barbell attachment
        self._pre_attach_hook(bodyset, jointset)

        # Exercise-specific attachment
        self.attach_barbell(jointset, body_bodies, barbell_bodies)

        # Exercise-specific initial pose
        self.set_initial_pose(jointset)

        # --- Ground contact geometry and forces ---
        add_contact_half_space(model, name="ground_contact", body="ground")
        add_foot_contact_spheres(model, self.body_spec)

        # Connect each foot contact sphere to the ground half-space
        foot_contact_names = [
            f"foot_{side}_{point}"
            for side in ("l", "r")
            for point in ("heel_medial", "heel_lateral", "toe_medial", "toe_lateral")
        ]
        for sphere_name in foot_contact_names:
            add_hunt_crossley_force(
                model,
                name=f"force_{sphere_name}",
                contact_geometry_1=sphere_name,
                contact_geometry_2="ground_contact",
            )

        # Subclass hook for additional contact surfaces
        self._post_contact_hook(model)

        xml_str = serialize_model(root)

        # Postconditions: well-formed XML and coordinate defaults within bounds
        parsed = ensure_valid_xml(xml_str)
        ensure_coordinates_within_bounds(parsed)

        logger.info("%s model built successfully", self.exercise_name)
        return xml_str
