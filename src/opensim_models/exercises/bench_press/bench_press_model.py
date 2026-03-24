"""Bench press model builder.

The lifter lies supine on a bench. The barbell is gripped in the hands
at approximately shoulder width. The model starts in the lockout position
(arms extended) and the motion descends the bar to the chest then presses
back to lockout.

Biomechanical notes:
- Primary movers: pectoralis major, anterior deltoid, triceps brachii
- The bench constrains pelvis and torso to a supine orientation
- Scapular retraction and arch are simplified (torso stays rigid on bench)
- Grip width affects shoulder abduction angle and pec activation

The bench is modelled as a ground-welded platform that constrains the
pelvis to a supine position at bench height (0.43 m, standard IPF).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from opensim_models.exercises.base import ExerciseConfig, ExerciseModelBuilder
from opensim_models.shared.utils.xml_helpers import (
    add_body,
    add_weld_joint,
    set_coordinate_default,
)

BENCH_HEIGHT = 0.43  # IPF standard bench height (meters)
BENCH_GRIP_HALF_WIDTH = 0.20  # meters from shaft center to each hand

# Bench box geometry (approximate dimensions for a standard IPF bench)
_BENCH_WIDTH = 0.30   # metres (X)
_BENCH_HEIGHT_DIM = 0.05  # metres (Y) — thickness of the padded top
_BENCH_DEPTH = 1.20   # metres (Z) — length of bench

# Inertia for bench (treated as massless rigid constraint body)
_BENCH_MASS = 1e-4   # near-zero mass (kg) — bench mass is borne by ground


class BenchPressModelBuilder(ExerciseModelBuilder):
    """Builds a bench-press OpenSim model.

    The pelvis is welded to ground in a supine orientation at bench height.
    The barbell shaft is welded to both hands at grip width.
    A bench body is welded to ground and the pelvis is welded to the bench
    in a supine (face-up) orientation.
    """

    def __init__(self, config: ExerciseConfig | None = None) -> None:
        super().__init__(config)

    @property
    def exercise_name(self) -> str:
        return "bench_press"

    def _add_bench_and_constraint(
        self,
        bodyset: ET.Element,
        jointset: ET.Element,
    ) -> None:
        """Add the bench body welded to ground and pelvis welded to bench.

        The bench sits at BENCH_HEIGHT. The pelvis is constrained supine
        (face-up): the Z-axis of the pelvis points up (+Z = superior when
        lying on back), so orientation is rotated 90° about X to go from
        the default standing Y-up to the supine Z-up posture.
        """
        from opensim_models.shared.utils.geometry import rectangular_prism_inertia

        bench_inertia = rectangular_prism_inertia(
            _BENCH_MASS, _BENCH_WIDTH, _BENCH_HEIGHT_DIM, _BENCH_DEPTH
        )

        add_body(
            bodyset,
            name="bench",
            mass=_BENCH_MASS,
            mass_center=(0, 0, 0),
            inertia_xx=bench_inertia[0],
            inertia_yy=bench_inertia[1],
            inertia_zz=bench_inertia[2],
        )

        # Weld bench to ground at bench height (top surface of bench at BENCH_HEIGHT)
        add_weld_joint(
            jointset,
            name="bench_to_ground",
            parent_body="ground",
            child_body="bench",
            location_in_parent=(0, BENCH_HEIGHT, 0),
            location_in_child=(0, 0, 0),
        )

        # Weld pelvis to bench in supine orientation.
        # Supine: lifter lies face-up; pelvis Y-axis (long axis when standing)
        # becomes the Z-axis. Rotate 90° about X (pi/2) to achieve this.
        import math

        add_weld_joint(
            jointset,
            name="pelvis_to_bench",
            parent_body="bench",
            child_body="pelvis",
            location_in_parent=(0, 0, 0),
            location_in_child=(0, 0, 0),
        )
        # Set supine orientation on the pelvis_to_bench child frame
        # by patching the child frame orientation after creation
        bench_pelvis_joint = None
        for j in jointset.findall("WeldJoint"):
            if j.get("name") == "pelvis_to_bench":
                bench_pelvis_joint = j
                break
        if bench_pelvis_joint is not None:
            child_frame = bench_pelvis_joint.find("PhysicalOffsetFrame[@name='pelvis_to_bench_child']")
            if child_frame is not None:
                orient_el = child_frame.find("orientation")
                if orient_el is not None:
                    # Rotate 90° about X-axis: (pi/2, 0, 0) in body-fixed XYZ
                    orient_el.text = f"{math.pi / 2:.6f} 0.000000 0.000000"

    def attach_barbell(
        self,
        jointset: ET.Element,
        body_bodies: dict[str, ET.Element],
        barbell_bodies: dict[str, ET.Element],
    ) -> None:
        """Weld barbell to both hands at grip width.

        The grip is approximately shoulder-width (~0.40 m from center
        on each side for a standard grip).
        """
        add_weld_joint(
            jointset,
            name="barbell_to_left_hand",
            parent_body="hand_l",
            child_body="barbell_shaft",
            location_in_parent=(0, 0, 0),
            location_in_child=(-BENCH_GRIP_HALF_WIDTH, 0, 0),
        )

        add_weld_joint(
            jointset,
            name="barbell_to_right_hand",
            parent_body="hand_r",
            child_body="barbell_shaft",
            location_in_parent=(0, 0, 0),
            location_in_child=(BENCH_GRIP_HALF_WIDTH, 0, 0),
        )

    def set_initial_pose(self, jointset: ET.Element) -> None:
        """Set supine lockout position.

        Shoulders flexed ~90 deg (arms pointing up), elbows near-extended.
        The supine orientation is enforced by the bench–pelvis weld constraint.
        """
        shoulder_flex = 1.5708  # ~90 degrees (arms vertical)
        for side in ("l", "r"):
            set_coordinate_default(jointset, f"shoulder_{side}_flex", shoulder_flex)

    def build(self) -> str:
        """Build the complete bench press OpenSim model XML string.

        Extends the base build() to inject the bench body and the
        pelvis-to-bench weld constraint before serialisation.
        """
        import xml.etree.ElementTree as _ET

        from opensim_models.shared.barbell import create_barbell_bodies
        from opensim_models.shared.body import create_full_body
        from opensim_models.shared.contracts.postconditions import ensure_valid_xml
        from opensim_models.shared.utils.xml_helpers import serialize_model

        root = _ET.Element("OpenSimDocument", Version="40500")
        model = _ET.SubElement(root, "Model", name=self.exercise_name)

        gravity = _ET.SubElement(model, "gravity")
        g = self.config.gravity
        gravity.text = f"{g[0]:.6f} {g[1]:.6f} {g[2]:.6f}"

        ground_el = _ET.SubElement(model, "Ground", name="ground")
        _ET.SubElement(ground_el, "mass").text = "0"
        _ET.SubElement(ground_el, "mass_center").text = "0 0 0"
        _ET.SubElement(ground_el, "inertia").text = "0 0 0 0 0 0"

        bodyset = _ET.SubElement(model, "BodySet")
        jointset = _ET.SubElement(model, "JointSet")

        body_bodies = create_full_body(bodyset, jointset, self.config.body_spec)
        barbell_bodies = create_barbell_bodies(bodyset, jointset, self.config.barbell_spec)

        # Add bench body and pelvis constraint (bench-press specific)
        self._add_bench_and_constraint(bodyset, jointset)

        self.attach_barbell(jointset, body_bodies, barbell_bodies)
        self.set_initial_pose(jointset)

        xml_str = serialize_model(root)
        ensure_valid_xml(xml_str)
        return xml_str


def build_bench_press_model(
    body_mass: float = 80.0,
    height: float = 1.75,
    plate_mass_per_side: float = 50.0,
) -> str:
    """Convenience function to build a bench press model XML string."""
    from opensim_models.shared.barbell import BarbellSpec
    from opensim_models.shared.body import BodyModelSpec

    config = ExerciseConfig(
        body_spec=BodyModelSpec(total_mass=body_mass, height=height),
        barbell_spec=BarbellSpec.mens_olympic(plate_mass_per_side=plate_mass_per_side),
    )
    return BenchPressModelBuilder(config).build()
