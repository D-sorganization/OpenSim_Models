"""Offline unit tests for ForwardSimulationTool and result structures."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from opensim_models.tools._types import ForwardSimulationResult
from opensim_models.tools.forward_simulation import (
    ForwardSimulationTool,
    add_coordinate_actuators,
    run_forward_simulation,
)


def test_forward_simulation_result_dataclass(tmp_path: Path) -> None:
    """ForwardSimulationResult stores coordinates/speeds and converts to degrees."""
    times = np.array([0.0, 0.05, 0.10])
    coords = {
        "knee_r_flex": np.array([0.0, -0.1, -0.2]),
        "pelvis_ty": np.array([0.95, 0.94, 0.93]),
    }
    speeds = {
        "knee_r_flex": np.array([0.0, -1.0, -1.0]),
        "pelvis_ty": np.array([0.0, -0.1, -0.1]),
    }
    result = ForwardSimulationResult(
        time=times,
        coordinates=coords,
        speeds=speeds,
        min_pelvis_height=0.93,
        collapsed=False,
        states_file=tmp_path / "states.sto",
        column_labels=["time", "knee_r_flex", "pelvis_ty"],
    )

    assert result.min_pelvis_height == pytest.approx(0.93)
    assert not result.collapsed
    assert result.states_file == tmp_path / "states.sto"

    # Coordinates in radians and degrees
    rad_vals = result.get_coordinate_values("knee_r_flex")
    np.testing.assert_allclose(rad_vals, [0.0, -0.1, -0.2])
    deg_vals = result.get_coordinate_values("knee_r_flex", in_degrees=True)
    np.testing.assert_allclose(deg_vals, np.rad2deg([0.0, -0.1, -0.2]))

    # Speeds in rad/s and deg/s
    rad_speeds = result.get_coordinate_speeds("knee_r_flex")
    np.testing.assert_allclose(rad_speeds, [0.0, -1.0, -1.0])
    deg_speeds = result.get_coordinate_speeds("knee_r_flex", in_degrees=True)
    np.testing.assert_allclose(deg_speeds, np.rad2deg([0.0, -1.0, -1.0]))

    # KeyError for missing coordinate
    with pytest.raises(KeyError, match="not found in results"):
        result.get_coordinate_values("unknown_coord")

    with pytest.raises(KeyError, match="not found in results"):
        result.get_coordinate_speeds("unknown_coord")


def test_offline_opensim_not_installed_raises_runtime_error() -> None:
    """When opensim is None, all APIs raise RuntimeError."""
    with patch("opensim_models.tools.forward_simulation.opensim", None):
        with pytest.raises(RuntimeError, match="OpenSim is not installed"):
            add_coordinate_actuators(None)

        with pytest.raises(RuntimeError, match="OpenSim is not installed"):
            ForwardSimulationTool("gait")

        with pytest.raises(RuntimeError, match="OpenSim is not installed"):
            run_forward_simulation("gait")


def test_forward_simulation_input_validation() -> None:
    """Preconditions validate parameter bounds."""
    mock_osim = patch("opensim_models.tools.forward_simulation.opensim")
    mock_validate = patch(
        "opensim_models.tools.forward_simulation.validate_and_load_model"
    )
    with mock_osim, mock_validate:
        # duration <= initial_time
        with pytest.raises(ValueError, match="duration must be strictly greater"):
            ForwardSimulationTool("gait", duration=0.0, initial_time=0.0)

        # dt <= 0
        with pytest.raises(ValueError, match="dt must be positive"):
            ForwardSimulationTool("gait", duration=1.0, dt=-0.01)

        # dt > duration - initial_time
        with pytest.raises(ValueError, match="dt must be positive and <="):
            ForwardSimulationTool("gait", duration=0.1, dt=0.5)

        # accuracy <= 0
        with pytest.raises(ValueError, match="accuracy must be positive"):
            ForwardSimulationTool("gait", duration=1.0, accuracy=-1e-4)

        # collapse_threshold NaN
        with pytest.raises(ValueError, match="collapse_threshold must be finite"):
            ForwardSimulationTool("gait", duration=1.0, collapse_threshold=float("nan"))
