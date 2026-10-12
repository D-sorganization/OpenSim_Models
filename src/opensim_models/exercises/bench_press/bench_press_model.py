"""Bench press model builder.

The lifter lies supine on a bench. The barbell is gripped at the palm
centres at the spec grip width. The default state is the standard's bench
press ``start`` via-pose (unrack, UpstreamDrift#11743): the bar over the
shoulders, the feet flat on the floor at the spec stance. The motion
descends the bar to the chest then presses back to lockout.

Biomechanical notes:
- Primary movers: pectoralis major, anterior deltoid, triceps brachii
- The bench constrains pelvis and torso to a supine orientation
- Scapular retraction and arch are simplified (torso stays rigid on bench)
- Grip width affects shoulder abduction angle and pec activation

The bench is modelled as a ground-welded platform (top at 0.43 m, standard
IPF); the pelvis is welded to it at the spec start root pose.
"""

from __future__ import annotations

import logging
import math
import xml.etree.ElementTree as ET

import numpy as np

from opensim_models.exercises.spec_start import (
    START,
    SpecLiftModelBuilder,
    spec_lift_config,
)
from opensim_models.shared.parity import via_poses
from opensim_models.shared.utils.contact_helpers import (
    add_contact_half_space,
    add_contact_sphere,
    add_hunt_crossley_force,
)
from opensim_models.shared.utils.geometry import rectangular_prism_inertia
from opensim_models.shared.utils.xml_helpers import add_body, add_weld_joint

logger = logging.getLogger(__name__)

BENCH_HEIGHT = 0.43  # IPF standard bench height (meters)

# Bench box geometry (approximate dimensions for a standard IPF bench)
_BENCH_LENGTH = 1.20  # metres (X) — along the supine lifter's long axis
_BENCH_HEIGHT_DIM = 0.05  # metres (Y) — thickness of the padded top
_BENCH_WIDTH = 0.30  # metres (Z) — lateral

# Inertia for bench (treated as massless rigid constraint body)
_BENCH_MASS = 1e-4  # near-zero mass (kg) — bench mass is borne by ground


class BenchPressModelBuilder(SpecLiftModelBuilder):
    """Builds a bench-press OpenSim model.

    A bench body is welded to ground and the pelvis is welded to the bench
    in the supine (face-up) root pose of the spec ``start`` via-pose
    (standard ``root_joint: weld``). The barbell shaft is welded to both
    palm centres at the spec grip.
    """

    @property
    def exercise_name(self) -> str:
        return "bench_press"

    @property
    def spec_exercise(self) -> str:
        return "bench_press"

    def _add_bench_body(self, bodyset: ET.Element) -> None:
        """Add the bench rigid body to *bodyset* with near-zero mass."""
        bench_inertia = rectangular_prism_inertia(
            _BENCH_MASS, _BENCH_LENGTH, _BENCH_HEIGHT_DIM, _BENCH_WIDTH
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

    def _weld_bench_to_ground(self, jointset: ET.Element) -> None:
        """Weld the bench body to ground at BENCH_HEIGHT."""
        add_weld_joint(
            jointset,
            name="bench_to_ground",
            parent_body="ground",
            child_body="bench",
            location_in_parent=(0, BENCH_HEIGHT, 0),
            location_in_child=(0, 0, 0),
        )

    def _weld_pelvis_to_bench_supine(self, jointset: ET.Element) -> None:
        """Weld the pelvis to the bench at the spec start root pose.

        Supine: the spec root pitch is -pi/2, so the pelvis anterior X-axis
        points up (+Y) and its long Y-axis along -X (head end). The weld
        holds the spec root position and orientation (UpstreamDrift#11743);
        the bench origin sits at ``BENCH_HEIGHT`` on the ground's Y axis.
        """
        position = via_poses.root_position(self.spec_exercise, START, self.height)
        location = position - np.array((0.0, BENCH_HEIGHT, 0.0))
        add_weld_joint(
            jointset,
            name="pelvis_to_bench",
            parent_body="bench",
            child_body="pelvis",
            location_in_parent=(
                float(location[0]),
                float(location[1]),
                float(location[2]),
            ),
            orientation_in_parent=via_poses.body_xyz_angles(
                via_poses.root_rotation(self.spec_exercise, START)
            ),
        )

    def _add_bench_and_constraint(
        self,
        bodyset: ET.Element,
        jointset: ET.Element,
    ) -> None:
        """Add the bench body welded to ground and pelvis welded to bench."""
        self._add_bench_body(bodyset)
        self._weld_bench_to_ground(jointset)
        self._weld_pelvis_to_bench_supine(jointset)

    def _skip_ground_joint(self) -> bool:
        """Bench press supplies its own pelvis parent via WeldJoint to bench."""
        return True

    def _pre_attach_hook(self, bodyset: ET.Element, jointset: ET.Element) -> None:
        """Inject the bench body and pelvis-to-bench constraint."""
        self._add_bench_and_constraint(bodyset, jointset)

    def _post_contact_hook(self, model: ET.Element) -> None:
        """Add bench contact surface and pelvis-to-bench contact force."""
        add_contact_half_space(
            model,
            name="bench_contact",
            body="bench",
            location=(0, _BENCH_HEIGHT_DIM / 2.0, 0),
            orientation=(0, 0, -math.pi / 2),
        )
        add_contact_sphere(
            model,
            name="pelvis_contact",
            body="pelvis",
            location=(0, -0.05, 0),
            radius=0.05,
        )
        add_hunt_crossley_force(
            model,
            name="force_pelvis_bench",
            contact_geometry_1="pelvis_contact",
            contact_geometry_2="bench_contact",
        )


def build_bench_press_model(
    body_mass: float = 80.0,
    height: float = 1.75,
    plate_mass_per_side: float | None = None,
) -> str:
    """Convenience function to build a bench press model XML string.

    ``plate_mass_per_side=None`` is the spec load.
    """
    config = spec_lift_config("bench_press", body_mass, height, plate_mass_per_side)
    return BenchPressModelBuilder(config).build()
