"""Gait (walking) model builder.

Builds an OpenSim model configured for walking gait analysis. No barbell
is attached; the model represents an unloaded human body in a natural
walking initial pose.

Biomechanical notes:
- Primary movers: hip flexors/extensors, quadriceps, hamstrings,
  gastrocnemius/soleus, tibialis anterior
- The model captures sagittal-plane gait kinematics
- Initial pose: mid-stance with slight hip and knee flexion
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

from opensim_models.exercises.base import ExerciseConfig, ExerciseModelBuilder
from opensim_models.shared.utils.xml_helpers import set_coordinate_default

logger = logging.getLogger(__name__)


class GaitModelBuilder(ExerciseModelBuilder):
    """Builds a walking gait OpenSim model.

    No barbell is used. The model starts in a mid-stance walking pose
    with slight hip and knee flexion on the stance leg.
    """

    @property
    def exercise_name(self) -> str:
        return "gait"

    @property
    def uses_barbell(self) -> bool:
        return False

    def attach_barbell(
        self,
        jointset: ET.Element,
        body_bodies: dict[str, ET.Element],
        barbell_bodies: dict[str, ET.Element],
    ) -> None:
        """No-op: gait analysis does not use a barbell."""

    def set_initial_pose(self, jointset: ET.Element) -> None:
        """Set mid-stance walking pose.

        Right leg in stance (slight flexion), left leg in swing
        (moderate hip flexion, knee flexion).
        """
        # Stance leg (right): slight flexion
        set_coordinate_default(jointset, "hip_r_flex", 0.0873)  # ~5 deg extension
        set_coordinate_default(jointset, "hip_r_adduct", 0.0)
        set_coordinate_default(jointset, "hip_r_rotate", 0.0)
        set_coordinate_default(jointset, "knee_r_flex", -0.0873)  # ~5 deg flexion
        set_coordinate_default(jointset, "ankle_r_flex", 0.0)
        set_coordinate_default(jointset, "ankle_r_inversion", 0.0)

        # Swing leg (left): moderate flexion
        set_coordinate_default(jointset, "hip_l_flex", 0.3491)  # ~20 deg
        set_coordinate_default(jointset, "hip_l_adduct", 0.0)
        set_coordinate_default(jointset, "hip_l_rotate", 0.0)
        set_coordinate_default(jointset, "knee_l_flex", -0.5236)  # ~30 deg
        set_coordinate_default(jointset, "ankle_l_flex", 0.0873)  # ~5 deg dorsiflexion
        set_coordinate_default(jointset, "ankle_l_inversion", 0.0)


def build_gait_model(
    body_mass: float = 80.0,
    height: float = 1.75,
) -> str:
    """Convenience function to build a gait model XML string.

    Default: 80 kg person, 1.75 m tall, no barbell.
    The plate_mass_per_side parameter is accepted for CLI compatibility
    but ignored (no barbell in gait).
    """
    from opensim_models.shared.barbell import BarbellSpec
    from opensim_models.shared.body import BodyModelSpec

    config = ExerciseConfig(
        body_spec=BodyModelSpec(total_mass=body_mass, height=height),
        barbell_spec=BarbellSpec.mens_olympic(plate_mass_per_side=0.0),
    )
    return GaitModelBuilder(config).build()
