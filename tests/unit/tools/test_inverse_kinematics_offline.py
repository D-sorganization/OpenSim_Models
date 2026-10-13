"""Engine-free unit tests for InverseKinematicsTool and TRC utilities."""

from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from opensim_models.tools._trc import write_trc_file
from opensim_models.tools._types import InverseKinematicsResult
from opensim_models.tools._validation import (
    validate_ik_times,
    validate_marker_trajectories,
    validate_marker_weights,
)
from opensim_models.tools.inverse_kinematics import (
    InverseKinematicsTool,
    run_inverse_kinematics,
)


def test_write_trc_file_structure(tmp_path: Path) -> None:
    """write_trc_file writes standard TRC format with valid headers and coordinates."""
    trc_path = tmp_path / "trial.trc"
    times = [0.0, 0.01, 0.02]
    markers = {
        "m_head": [[0.0, 1.6, 0.0], [0.0, 1.61, 0.0], [0.0, 1.62, 0.0]],
        "m_sternum": [[0.0, 1.3, 0.1], [0.0, 1.3, 0.1], [0.0, 1.3, 0.1]],
    }
    written = write_trc_file(trc_path, times, markers, units="m")
    assert written == trc_path
    assert trc_path.is_file()

    content = trc_path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    assert len(lines) == 5 + len(times)

    # Line 1: PathFileType
    assert lines[0].startswith("PathFileType\t4\t(X/Y/Z)\ttrial.trc")

    # Line 2: Header keywords
    assert "DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits" in lines[1]

    # Line 3: Header values
    row3 = lines[2].split("\t")
    assert row3[2] == "3"  # NumFrames
    assert row3[3] == "2"  # NumMarkers
    assert row3[4] == "m"  # Units

    # Line 4: Marker column names
    row4 = lines[3].split("\t")
    assert row4[0] == "Frame#"
    assert row4[1] == "Time"
    assert "m_head" in row4
    assert "m_sternum" in row4

    # Line 5: Coordinate components
    row5 = lines[4].split("\t")
    assert row5[2:5] == ["X1", "Y1", "Z1"]
    assert row5[5:8] == ["X2", "Y2", "Z2"]

    # Line 6: First frame
    row6 = lines[5].split("\t")
    assert row6[0] == "1"
    assert float(row6[1]) == pytest.approx(0.0)
    assert float(row6[2]) == pytest.approx(0.0)
    assert float(row6[3]) == pytest.approx(1.6)
    assert float(row6[4]) == pytest.approx(0.0)


def test_inverse_kinematics_result_dataclass(tmp_path: Path) -> None:
    """InverseKinematicsResult provides radian coordinates and degrees conversion."""
    times = np.array([0.0, 0.01])
    # Rotational coordinate in radians: 0.5 rad ~ 28.6479 deg
    coords = {
        "pelvis_tilt": np.array([0.5, 0.6]),
        "pelvis_ty": np.array([0.9, 0.9]),
    }
    result = InverseKinematicsResult(
        motion_file=tmp_path / "out.mot",
        time=times,
        coordinates=coords,
        column_labels=["time", "pelvis_tilt", "pelvis_ty"],
        in_degrees=True,
    )

    assert result.motion_file == tmp_path / "out.mot"
    np.testing.assert_array_equal(result.time, times)

    # In radians (default)
    rad_vals = result.get_coordinate_values("pelvis_tilt")
    np.testing.assert_allclose(rad_vals, [0.5, 0.6])

    # In degrees
    deg_vals = result.get_coordinate_values("pelvis_tilt", in_degrees=True)
    np.testing.assert_allclose(deg_vals, np.rad2deg([0.5, 0.6]))

    # get_coordinate_value alias
    alias_vals = result.get_coordinate_value("pelvis_tilt")
    np.testing.assert_array_equal(alias_vals, rad_vals)

    # KeyError for missing coordinate
    with pytest.raises(KeyError, match="not found in results"):
        result.get_coordinate_values("unknown_coord")


def test_offline_opensim_not_installed_raises_runtime_error() -> None:
    """When opensim is None, InverseKinematicsTool raises RuntimeError."""
    with patch("opensim_models.tools.inverse_kinematics.opensim", None):
        with pytest.raises(RuntimeError, match="OpenSim is not installed"):
            InverseKinematicsTool("gait")

        with pytest.raises(RuntimeError, match="OpenSim is not installed"):
            run_inverse_kinematics("gait")


def test_validate_ik_times() -> None:
    """validate_ik_times verifies strictly increasing finite timestamps."""
    # None when no markers
    assert validate_ik_times(None, None) is None

    # Error if markers present without times
    with pytest.raises(ValueError, match="times sequence is required"):
        validate_ik_times(None, {"m": [[0, 0, 0]]})

    # Empty times
    with pytest.raises(ValueError, match="must not be empty"):
        validate_ik_times([], None)

    # Not strictly increasing
    with pytest.raises(ValueError, match="strictly increasing"):
        validate_ik_times([0.0, 0.05, 0.05], None)

    # Non-finite
    with pytest.raises(ValueError):
        validate_ik_times([0.0, float("nan")], None)

    # Valid
    assert validate_ik_times([0.0, 0.01, 0.02], None) == [0.0, 0.01, 0.02]


def test_validate_marker_trajectories() -> None:
    """validate_marker_trajectories checks frame length, marker presence, and 3D coords."""
    model_markers = {"m1", "m2"}
    times = [0.0, 0.01]

    # None returns None
    assert validate_marker_trajectories(None, times, model_markers) is None

    # Unknown marker
    with pytest.raises(ValueError, match="not in the model marker set"):
        validate_marker_trajectories(
            {"m_unknown": [[0, 0, 0], [0, 0, 0]]}, times, model_markers
        )

    # Frame count mismatch
    with pytest.raises(ValueError, match="does not match times length"):
        validate_marker_trajectories({"m1": [[0, 0, 0]]}, times, model_markers)

    # Non-3D point
    with pytest.raises(ValueError, match="must have 3 coordinates"):
        validate_marker_trajectories({"m1": [[0, 0], [0, 0]]}, times, model_markers)

    # Non-finite coordinate
    with pytest.raises(ValueError):
        validate_marker_trajectories(
            {"m1": [[0, math.nan, 0], [0, 0, 0]]}, times, model_markers
        )

    # Valid
    valid = validate_marker_trajectories(
        {"m1": [[1, 2, 3], [4, 5, 6]]}, times, model_markers
    )
    assert valid == {"m1": [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]}


def test_validate_marker_weights() -> None:
    """validate_marker_weights validates presence in model and non-negativity."""
    model_markers = {"m1", "m2"}

    assert validate_marker_weights(None, model_markers) is None

    with pytest.raises(ValueError, match="not in the model marker set"):
        validate_marker_weights({"m_unknown": 1.0}, model_markers)

    with pytest.raises(ValueError, match="must be non-negative"):
        validate_marker_weights({"m1": -0.5}, model_markers)

    valid = validate_marker_weights({"m1": 2.0, "m2": 0.0}, model_markers)
    assert valid == {"m1": 2.0, "m2": 0.0}
