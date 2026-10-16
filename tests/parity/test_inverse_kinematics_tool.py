"""Real-engine inverse kinematics: recover known joint angles from marker trajectories."""

from __future__ import annotations

from pathlib import Path

import pytest

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.tools._trc import write_trc_file
from opensim_models.tools.inverse_kinematics import (
    InverseKinematicsResult,
    InverseKinematicsTool,
    run_inverse_kinematics,
)

pytestmark = pytest.mark.requires_opensim

try:
    import opensim
except ImportError:
    opensim = None

needs_opensim = pytest.mark.skipif(
    opensim is None,
    reason="opensim is not installed in this Python environment",
)


@needs_opensim
def test_inverse_kinematics_recovers_known_pose(tmp_path: Path) -> None:
    """Recover joint angles from synthetic forward kinematics markers within 0.15 rad."""
    osim_path = tmp_path / "gait.osim"
    osim_path.write_text(EXERCISE_BUILDERS["gait"](), encoding="utf-8")

    model = opensim.Model(str(osim_path))
    state = model.initSystem()

    # Pose with known rotations within valid ranges
    known_coords = {
        "hip_r_flex": 0.15,
        "knee_r_flex": -0.25,
        "hip_l_flex": -0.10,
        "knee_l_flex": -0.15,
    }

    coord_set = model.getCoordinateSet()
    for name, val in known_coords.items():
        coord_set.get(name).setValue(state, val)
    model.realizePosition(state)

    # Generate synthetic marker positions via forward kinematics
    marker_set = model.getMarkerSet()
    assert marker_set.getSize() > 0
    ground = model.getGround()

    times = [i * 0.01 for i in range(10)]
    synthetic_markers: dict[str, list[list[float]]] = {}
    for i in range(marker_set.getSize()):
        marker = marker_set.get(i)
        loc = marker.findLocationInFrame(state, ground)
        pos = [loc.get(0), loc.get(1), loc.get(2)]
        synthetic_markers[marker.getName()] = [pos for _ in times]

    tool = InverseKinematicsTool(
        model=model,
        marker_trajectories=synthetic_markers,
        times=times,
        results_dir=tmp_path / "ik_run",
    )
    result = tool.run()

    assert isinstance(result, InverseKinematicsResult)
    assert result.motion_file.is_file()
    assert len(result.time) == len(times)

    # Coordinates recovered within 0.15 rad (resolution limit for single-marker-per-segment kinematics)
    for name, expected_val in known_coords.items():
        recovered = result.get_coordinate_values(name)
        assert len(recovered) == len(times)
        for val in recovered:
            assert val == pytest.approx(expected_val, abs=0.15)


@needs_opensim
def test_run_inverse_kinematics_convenience_function(tmp_path: Path) -> None:
    """run_inverse_kinematics convenience function matches InverseKinematicsTool."""
    osim_path = tmp_path / "squat.osim"
    osim_path.write_text(EXERCISE_BUILDERS["squat"](), encoding="utf-8")

    model = opensim.Model(str(osim_path))
    state = model.initSystem()
    model.realizePosition(state)

    marker_set = model.getMarkerSet()
    ground = model.getGround()

    times = [0.0, 0.01, 0.02, 0.03, 0.04, 0.05]
    synthetic_markers: dict[str, list[list[float]]] = {}
    for i in range(marker_set.getSize()):
        marker = marker_set.get(i)
        loc = marker.findLocationInFrame(state, ground)
        pos = [loc.get(0), loc.get(1), loc.get(2)]
        synthetic_markers[marker.getName()] = [pos for _ in times]

    result = run_inverse_kinematics(
        model=model,
        marker_trajectories=synthetic_markers,
        times=times,
        results_dir=tmp_path / "squat_ik",
    )

    assert result.motion_file.is_file()
    assert len(result.time) == len(times)
    hip_r = result.get_coordinate_values("hip_r_flex")
    for val in hip_r:
        assert val == pytest.approx(0.0, abs=0.1)


@needs_opensim
def test_inverse_kinematics_from_exercise_name(tmp_path: Path) -> None:
    """InverseKinematicsTool accepts exercise name directly."""
    osim_path = tmp_path / "gait.osim"
    osim_path.write_text(EXERCISE_BUILDERS["gait"](), encoding="utf-8")
    model = opensim.Model(str(osim_path))
    state = model.initSystem()
    model.realizePosition(state)

    marker_set = model.getMarkerSet()
    ground = model.getGround()
    times = [0.0, 0.01, 0.02]
    synthetic_markers: dict[str, list[list[float]]] = {}
    for i in range(marker_set.getSize()):
        marker = marker_set.get(i)
        loc = marker.findLocationInFrame(state, ground)
        synthetic_markers[marker.getName()] = [
            [loc.get(0), loc.get(1), loc.get(2)] for _ in times
        ]

    result = run_inverse_kinematics(
        model="gait",
        marker_trajectories=synthetic_markers,
        times=times,
        results_dir=tmp_path / "named_ik",
    )
    assert result.motion_file.is_file()
    assert len(result.time) == len(times)


@needs_opensim
def test_inverse_kinematics_with_marker_file(tmp_path: Path) -> None:
    """InverseKinematicsTool executes from a pre-written .trc file."""
    osim_path = tmp_path / "gait.osim"
    osim_path.write_text(EXERCISE_BUILDERS["gait"](), encoding="utf-8")
    model = opensim.Model(str(osim_path))
    state = model.initSystem()
    model.realizePosition(state)

    marker_set = model.getMarkerSet()
    ground = model.getGround()
    times = [0.0, 0.01, 0.02]
    synthetic_markers: dict[str, list[list[float]]] = {}
    for i in range(marker_set.getSize()):
        marker = marker_set.get(i)
        loc = marker.findLocationInFrame(state, ground)
        synthetic_markers[marker.getName()] = [
            [loc.get(0), loc.get(1), loc.get(2)] for _ in times
        ]

    trc_file = write_trc_file(tmp_path / "input.trc", times, synthetic_markers)
    tool = InverseKinematicsTool(
        model=model,
        marker_file=trc_file,
        results_dir=tmp_path / "from_file_ik",
    )
    result = tool.run()
    assert result.motion_file.is_file()
    assert len(result.time) == len(times)


@needs_opensim
def test_inverse_kinematics_with_marker_weights(tmp_path: Path) -> None:
    """InverseKinematicsTool accepts custom marker weights."""
    osim_path = tmp_path / "gait.osim"
    osim_path.write_text(EXERCISE_BUILDERS["gait"](), encoding="utf-8")
    model = opensim.Model(str(osim_path))
    state = model.initSystem()
    model.realizePosition(state)

    marker_set = model.getMarkerSet()
    ground = model.getGround()
    times = [0.0, 0.01, 0.02]
    synthetic_markers: dict[str, list[list[float]]] = {}
    for i in range(marker_set.getSize()):
        marker = marker_set.get(i)
        loc = marker.findLocationInFrame(state, ground)
        synthetic_markers[marker.getName()] = [
            [loc.get(0), loc.get(1), loc.get(2)] for _ in times
        ]

    weights = {"head": 10.0, "torso": 5.0}
    result = run_inverse_kinematics(
        model="gait",
        marker_trajectories=synthetic_markers,
        marker_weights=weights,
        times=times,
        results_dir=tmp_path / "weighted_ik",
    )
    assert result.motion_file.is_file()


@needs_opensim
def test_inverse_kinematics_input_validation(tmp_path: Path) -> None:
    """Input validation rejects invalid parameters with descriptive errors."""
    times = [0.0, 0.01, 0.02]
    markers = {"head": [[0, 1.6, 0]] * 3}

    # Invalid model
    with pytest.raises(ValueError, match="Model must be an opensim.Model"):
        InverseKinematicsTool(model=99999, times=times, marker_trajectories=markers)

    # Missing markers and file
    with pytest.raises(
        ValueError, match="Must specify marker_file or marker_trajectories"
    ):
        InverseKinematicsTool(model="gait")

    # Non-existent marker file
    with pytest.raises(FileNotFoundError, match="Marker file not found"):
        InverseKinematicsTool(model="gait", marker_file=tmp_path / "missing.trc")

    # Marker not in model
    with pytest.raises(ValueError, match="not in the model marker set"):
        InverseKinematicsTool(
            model="gait",
            times=times,
            marker_trajectories={"non_existent_marker": [[0, 0, 0]] * 3},
        )

    # Marker length mismatch
    with pytest.raises(ValueError, match="does not match times length"):
        InverseKinematicsTool(
            model="gait",
            times=times,
            marker_trajectories={"head": [[0, 1.6, 0]] * 5},
        )

    # Marker weight negative
    with pytest.raises(ValueError, match="must be non-negative"):
        InverseKinematicsTool(
            model="gait",
            times=times,
            marker_trajectories=markers,
            marker_weights={"head": -1.0},
        )

    # Unknown coordinate raises KeyError
    result = run_inverse_kinematics(
        model="gait",
        times=times,
        marker_trajectories=markers,
        results_dir=tmp_path / "val_run",
    )
    with pytest.raises(KeyError, match="not found in results"):
        result.get_coordinate_values("non_existent_coordinate")
