"""Moco-ready OpenSim models of the exercises, optionally reduced (#470).

Moco rejects a ``FreeJoint`` root, so the generated model's pelvis FreeJoint
is rewritten as the equivalent CustomJoint.  The model has no muscles: every
remaining coordinate gets a ``CoordinateActuator`` (on the pelvis these are
residual actuators).

A :class:`ModelReduction` shrinks the problem for fast solves: named joints
are welded at the model's default (start) pose, and the foot-ground contact
forces can be dropped, leaving the pelvis residuals to carry the body.  A
joint may only be welded when every keyframe holds its coordinates at that
default pose, so a reduced study tracks exactly the same keyframes.

Design by Contract:
    - Preconditions: OpenSim with Moco is importable (else RuntimeError);
      the exercise is registered (else KeyError); every keyframe coordinate
      is a model coordinate (else ValueError); each welded joint exists
      and its keyframe values stay within ``WELD_KEYFRAME_TOL_RAD`` of the
      default pose (else ValueError).
    - Postconditions: the model has no FreeJoint and exactly one actuator per
      coordinate; welded joints have no coordinates left.
"""

from __future__ import annotations

import math
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from opensim_models._messages import ERR_OPENSIM_NOT_INSTALLED
from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.optimization._types import ExerciseObjective
from opensim_models.shared.utils.xml_helpers import (
    replace_free_joints_with_custom_joints,
)
from opensim_models.tools.forward_simulation import add_coordinate_actuators

try:
    import opensim
except ImportError:
    opensim = None  # type: ignore[assignment]

# Optimal force (N*m, or N on the pelvis translations) of every coordinate
# actuator; controls are dimensionless multiples of it.
ACTUATOR_OPTIMAL_FORCE = 1000.0
# A welded coordinate's keyframes may differ from its default by at most this.
WELD_KEYFRAME_TOL_RAD = math.radians(0.5)
_CONTACT_FORCE_TAGS = frozenset({"SmoothSphereHalfSpaceForce"})


@dataclass(frozen=True)
class ModelReduction:
    """How far to reduce the generated model before building a study.

    Attributes:
        welded_joints: Joints welded at the model's default (start) pose.
        ground_contact: Keep the smooth foot-ground contact forces.
    """

    welded_joints: tuple[str, ...] = ()
    ground_contact: bool = True


FULL_MODEL = ModelReduction()

# Fixed-base reduction for fast solves of standing lifts whose keyframes hold
# the arms and neck still (the back squat): the pelvis, neck and arm joints are
# welded at the start pose and the foot contact is dropped, leaving the lumbar,
# hip, knee and ankle coordinates to track the keyframes.
FIXED_PELVIS_STILL_ARMS = ModelReduction(
    welded_joints=(
        "ground_pelvis",
        "neck",
        "shoulder_l",
        "shoulder_r",
        "elbow_l",
        "elbow_r",
        "wrist_l",
        "wrist_r",
    ),
    ground_contact=False,
)


def require_opensim() -> None:
    """Raise RuntimeError unless OpenSim with Moco is importable."""
    if opensim is None or not hasattr(opensim, "MocoStudy"):
        raise RuntimeError(ERR_OPENSIM_NOT_INSTALLED)


def moco_ready_osim(exercise: str, *, ground_contact: bool = True) -> str:
    """The exercise's generated ``.osim`` XML with no FreeJoint (Moco-ready).

    Raises:
        KeyError: *exercise* is not a registered exercise builder.
    """
    if exercise not in EXERCISE_BUILDERS:
        available = ", ".join(sorted(EXERCISE_BUILDERS))
        raise KeyError(f"Unknown exercise '{exercise}'. Available: {available}")
    root = ET.fromstring(EXERCISE_BUILDERS[exercise]())
    replace_free_joints_with_custom_joints(root)
    if not ground_contact:
        for parent in list(root.iter()):
            for child in [c for c in parent if c.tag in _CONTACT_FORCE_TAGS]:
                parent.remove(child)
    return ET.tostring(root, encoding="unicode")


def coordinate_names(model: Any) -> list[str]:
    """Names of every coordinate of *model*, in model order."""
    coords = model.getCoordinateSet()
    return [coords.get(i).getName() for i in range(coords.getSize())]


def _joint_coordinates(model: Any, joint_name: str) -> dict[str, float]:
    """Coordinate name -> default value of one joint."""
    joints = model.getJointSet()
    if not joints.contains(joint_name):
        raise ValueError(f"cannot weld unknown joint {joint_name!r}")
    joint = joints.get(joint_name)
    return {
        joint.get_coordinates(i).getName(): joint.get_coordinates(i).getDefaultValue()
        for i in range(joint.numCoordinates())
    }


def _require_keyframe_coordinates(model: Any, objective: ExerciseObjective) -> None:
    """Every keyframe coordinate exists in the (unreduced) model."""
    targeted = {name for phase in objective.phases for name in phase.joint_targets}
    missing = sorted(targeted - set(coordinate_names(model)))
    if missing:
        raise ValueError(
            f"{objective.name}: keyframe coordinates {missing} not in model"
        )


def _require_static_keyframes(
    defaults: dict[str, float], objective: ExerciseObjective
) -> None:
    """Every keyframe holds the welded coordinates at their default values."""
    for phase in objective.phases:
        for name, default in defaults.items():
            target = phase.joint_targets.get(name, default)
            if abs(target - default) > WELD_KEYFRAME_TOL_RAD:
                raise ValueError(
                    f"cannot weld {name}: phase {phase.name!r} targets "
                    f"{target:.4f} rad, default pose is {default:.4f} rad"
                )


def _weld(model: Any, joints: tuple[str, ...], objective: ExerciseObjective) -> Any:
    for joint in joints:
        _require_static_keyframes(_joint_coordinates(model, joint), objective)
    processor = opensim.ModelProcessor(model)
    processor.append(opensim.ModOpReplaceJointsWithWelds(list(joints)))
    return processor.process()


def build_moco_model(
    objective: ExerciseObjective, reduction: ModelReduction = FULL_MODEL
) -> Any:
    """Load the Moco-ready model of *objective*, reduce it and actuate it.

    Returns:
        An initialised ``opensim.Model`` with one ``CoordinateActuator`` per
        remaining coordinate.
    """
    require_opensim()
    xml = moco_ready_osim(objective.name, ground_contact=reduction.ground_contact)
    with tempfile.TemporaryDirectory(prefix="opensim_moco_") as tmp:
        path = Path(tmp) / f"{objective.name}.osim"
        path.write_text(xml, encoding="utf-8")
        model = opensim.Model(str(path))
    _require_keyframe_coordinates(model, objective)
    if reduction.welded_joints:
        model = _weld(model, reduction.welded_joints, objective)
    add_coordinate_actuators(
        model, ACTUATOR_OPTIMAL_FORCE, coordinates=coordinate_names(model)
    )
    model.finalizeConnections()
    model.initSystem()
    return model
