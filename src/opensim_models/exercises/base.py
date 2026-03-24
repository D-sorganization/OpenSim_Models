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

from opensim_models.shared.barbell import BarbellSpec, create_barbell_bodies
from opensim_models.shared.body import BodyModelSpec, create_full_body
from opensim_models.shared.contracts.postconditions import ensure_valid_xml
from opensim_models.shared.utils.xml_helpers import serialize_model

logger = logging.getLogger(__name__)


@dataclass
class ExerciseConfig:
    """Configuration common to all exercise models."""

    body_spec: BodyModelSpec = field(default_factory=BodyModelSpec)
    barbell_spec: BarbellSpec = field(default_factory=BarbellSpec.mens_olympic)
    gravity: tuple[float, float, float] = (0.0, -9.80665, 0.0)


class ExerciseModelBuilder(ABC):
    """Abstract builder for exercise-specific OpenSim models.

    Subclasses must implement:
      - exercise_name: str property
      - attach_barbell(): how the barbell connects to the body
      - set_initial_pose(): default coordinate values for the start position
    """

    def __init__(self, config: ExerciseConfig | None = None) -> None:
        self.config = config or ExerciseConfig()

    @property
    @abstractmethod
    def exercise_name(self) -> str:
        """Human-readable exercise name used in the model XML."""

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

    def _pre_attach_hook(  # noqa: B027
        self, bodyset: ET.Element, jointset: ET.Element
    ) -> None:
        """Hook called after bodies are built, before barbell is attached.

        Subclasses may override to inject additional bodies or joints
        (e.g. a bench body and constraint for bench press).
        The default implementation is a no-op.
        """

    def _skip_ground_joint(self) -> bool:
        """Return True if the pelvis–ground FreeJoint should be omitted.

        Override in subclasses that supply their own pelvis parent joint
        (e.g. bench press, where pelvis is welded to the bench body).
        """
        return False

    def build(self) -> str:
        """Build the complete OpenSim model XML and return as string.

        Postcondition: returned string is well-formed XML.
        """
        logger.info("Building %s model", self.exercise_name)
        root = ET.Element("OpenSimDocument", Version="40500")
        model = ET.SubElement(root, "Model", name=self.exercise_name)

        # Gravity
        gravity = ET.SubElement(model, "gravity")
        g = self.config.gravity
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
            self.config.body_spec,
            skip_ground_joint=self._skip_ground_joint(),
        )

        # Build barbell
        barbell_bodies = create_barbell_bodies(
            bodyset, jointset, self.config.barbell_spec
        )

        # Subclass hook: inject extra bodies/joints before barbell attachment
        self._pre_attach_hook(bodyset, jointset)

        # Exercise-specific attachment
        self.attach_barbell(jointset, body_bodies, barbell_bodies)

        # Exercise-specific initial pose
        self.set_initial_pose(jointset)

        xml_str = serialize_model(root)

        # Postcondition: well-formed XML
        ensure_valid_xml(xml_str)

        logger.info("%s model built successfully", self.exercise_name)
        return xml_str
