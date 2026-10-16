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
from opensim_models.shared.body import (
    BodyModelSpec,
    add_foot_contact_spheres,
    add_standard_markers,
    create_full_body,
)
from opensim_models.shared.body.foot_seating import (
    foot_seating_offset,
    lower_foot_contact_spheres,
)
from opensim_models.shared.body.ground_placement import standing_pelvis_height
from opensim_models.shared.body.lumbar_chain import (
    LumbarCouplingLaw,
    require_lumbar_law,
)
from opensim_models.shared.contact import foot_sphere_names
from opensim_models.shared.contracts.postconditions import (
    ensure_coordinates_within_bounds,
)
from opensim_models.shared.utils.constraint_helpers import get_constraint_set
from opensim_models.shared.utils.contact_helpers import (
    add_contact_half_space,
    add_hunt_crossley_force,
)
from opensim_models.shared.utils.xml_helpers import (
    serialize_model,
    set_coordinate_defaults,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExerciseConfig:
    """Configuration common to all exercise models."""

    body_spec: BodyModelSpec = field(default_factory=BodyModelSpec)
    barbell_spec: BarbellSpec = field(default_factory=BarbellSpec.mens_olympic)
    gravity: tuple[float, float, float] = (0.0, -9.80665, 0.0)
    # Shaft centre to palm centre (metres). None: the exercise's own grip; a
    # spec lift (``spec_start.py``) accepts only its standard grip width.
    grip_offset: float | None = None
    # Opt-in segmental lumbar chain (#464). None keeps the single lumbar joint
    # and a byte-identical model; a law replaces it by five coupled levels.
    lumbar_chain: LumbarCouplingLaw | None = None

    def __post_init__(self) -> None:
        require_lumbar_law(self.lumbar_chain)


class ExerciseModelBuilder(ABC):
    """Abstract builder for exercise-specific OpenSim models.

    Subclasses must implement:
      - exercise_name: str property
      - attach_barbell(): how the barbell connects to the body
      - set_initial_pose(): default coordinate values for the start position
    """

    # Seat the foot spheres at the contact-law equilibrium depth (#472, as
    # MuJoCo_Models#447/#453): the free-root standing models set it.
    seat_feet_at_equilibrium: bool = False

    def __init__(self, config: ExerciseConfig | None = None) -> None:
        self.config = config or ExerciseConfig()
        # Model element under construction; set by build() so attachment
        # hooks can add constraints (a body has only one parent joint).
        self._model_el: ET.Element = ET.Element("Model")

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
    def grip_offset(self) -> float | None:
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

    def _initial_pelvis_height(self, model: ET.Element) -> float:
        """Default ``pelvis_ty``: lowest foot sphere touches y = 0 (#381)."""
        return standing_pelvis_height(model)

    def _initial_root_coordinates(self, model: ET.Element) -> dict[str, float]:
        """Default pelvis FreeJoint coordinates (upright, feet on the floor).

        Spec lifts override this with their ``start`` via-pose root.
        """
        return {"pelvis_ty": self._initial_pelvis_height(model)}

    def _post_contact_hook(  # noqa: B027 -- intentional no-op hook, not a missing abstract
        self, model: ET.Element
    ) -> None:
        """Hook called after standard ground contact is added.

        Subclasses may override to inject additional contact surfaces
        (e.g. a bench contact surface for bench press).
        The default implementation is a no-op.
        """

    def _create_model_root(self) -> tuple[ET.Element, ET.Element]:
        """Create the OpenSim document root and Model element."""
        root = ET.Element("OpenSimDocument", Version="40500")
        model = ET.SubElement(root, "Model", name=self.exercise_name)
        return root, model

    def _add_gravity_and_ground(self, model: ET.Element) -> None:
        """Append gravity vector and massless Ground body to the model."""
        gravity = ET.SubElement(model, "gravity")
        g = self.gravity
        gravity.text = f"{g[0]:.6f} {g[1]:.6f} {g[2]:.6f}"

        ground_el = ET.SubElement(model, "Ground", name="ground")
        ET.SubElement(ground_el, "mass").text = "0"
        ET.SubElement(ground_el, "mass_center").text = "0 0 0"
        ET.SubElement(ground_el, "inertia").text = "0 0 0 0 0 0"

    def _build_bodies_and_joints(
        self, model: ET.Element
    ) -> tuple[ET.Element, ET.Element, dict[str, ET.Element], dict[str, ET.Element]]:
        """Build body/joint sets, populate them, and return the sets and body dicts."""
        bodyset = ET.SubElement(model, "BodySet")
        jointset = ET.SubElement(model, "JointSet")

        law = self.config.lumbar_chain
        body_bodies = create_full_body(
            bodyset,
            jointset,
            self.body_spec,
            skip_ground_joint=self._skip_ground_joint(),
            lumbar_chain=law,
            constraintset=None if law is None else get_constraint_set(model),
        )
        if law is not None:
            # Record the coupling law in force in the model metadata.
            ET.SubElement(model, "publications").text = law.provenance

        barbell_bodies: dict[str, ET.Element] = {}
        if self.uses_barbell:
            barbell_bodies = create_barbell_bodies(bodyset, jointset, self.barbell_spec)

        return bodyset, jointset, body_bodies, barbell_bodies

    def _add_ground_contact(self, model: ET.Element) -> None:
        """Add the ground contact half-space and foot sphere forces."""
        add_contact_half_space(model, name="ground_contact", body="ground")
        add_foot_contact_spheres(model, self.body_spec)

        for sphere_name in foot_sphere_names():
            add_hunt_crossley_force(
                model,
                name=f"force_{sphere_name}",
                contact_geometry_1=sphere_name,
                contact_geometry_2="ground_contact",
            )

    def _seat_feet(self, model: ET.Element) -> None:
        """Lower the foot spheres to the equilibrium depth (opt-in, #472)."""
        if self.seat_feet_at_equilibrium:
            lower_foot_contact_spheres(model, foot_seating_offset(model))

    def build(self) -> str:
        """Build the complete OpenSim model XML and return as string.

        Postcondition: returned string is well-formed XML.
        """
        logger.info("Building %s model", self.exercise_name)
        root, model = self._create_model_root()
        self._model_el = model
        self._add_gravity_and_ground(model)

        bodyset, jointset, body_bodies, barbell_bodies = self._build_bodies_and_joints(
            model
        )

        # Subclass hook: inject extra bodies/joints before barbell attachment
        self._pre_attach_hook(bodyset, jointset)

        # Exercise-specific attachment and initial pose
        self.attach_barbell(jointset, body_bodies, barbell_bodies)
        self.set_initial_pose(jointset)

        # Ground contact geometry and forces, plus subclass hook
        self._add_ground_contact(model)
        self._post_contact_hook(model)
        if not self._skip_ground_joint():
            set_coordinate_defaults(jointset, self._initial_root_coordinates(model))
            self._seat_feet(model)

        # Standard MarkerSet (#387)
        add_standard_markers(model, self.body_spec, uses_barbell=self.uses_barbell)

        # Postconditions: coordinate defaults within bounds
        # ⚡ Bolt Optimization: Validate before serialization
        # What: Run ensure_coordinates_within_bounds before serialize_model.
        # Why: Fail-fast execution avoids redundant string stringification overhead if validation fails.
        # Impact: Improves performance in error paths by preventing unnecessary XML generation.
        ensure_coordinates_within_bounds(root)

        xml_str = serialize_model(root)

        logger.info("%s model built successfully", self.exercise_name)
        return xml_str
