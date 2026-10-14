"""Real-engine forward dynamics simulation: integrate with Manager and CoordinateActuators."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.tools.forward_simulation import (
    ForwardSimulationResult,
    ForwardSimulationTool,
    add_coordinate_actuators,
    run_forward_simulation,
)

try:
    import opensim
except ImportError:
    opensim = None

needs_opensim = pytest.mark.skipif(
    opensim is None or sys.version_info < (3, 11),
    reason="the opensim pip wheel is published for CPython 3.11+ only",
)


@needs_opensim
def test_forward_simulation_with_manager_and_actuators(tmp_path: Path) -> None:
    """Add CoordinateActuators, integrate with Manager, verify state evolves without blowup or collapse."""
    osim_path = tmp_path / "squat.osim"
    osim_path.write_text(EXERCISE_BUILDERS["squat"](), encoding="utf-8")

    model = opensim.Model(str(osim_path))
    added = add_coordinate_actuators(model, optimal_force=1000.0)
    assert len(added) > 0

    tool = ForwardSimulationTool(
        model=model,
        duration=0.2,
        dt=0.02,
        holding_controller=True,
        collapse_threshold=0.5,
    )
    result = tool.run()

    assert isinstance(result, ForwardSimulationResult)
    # State evolves across time
    assert len(result.time) > 1
    assert result.time[-1] == pytest.approx(0.2)

    # Model does not blow up: all coordinates and speeds are finite
    for name, arr in result.coordinates.items():
        assert len(arr) == len(result.time)
        assert np.all(np.isfinite(arr)), (
            f"Coordinate '{name}' contains non-finite values"
        )

    for name, arr in result.speeds.items():
        assert len(arr) == len(result.time)
        assert np.all(np.isfinite(arr)), f"Speed '{name}' contains non-finite values"

    # Model does not fall through the floor
    assert not result.collapsed
    assert result.min_pelvis_height > 0.6  # Starts near ~1.0 m


@needs_opensim
def test_run_forward_simulation_convenience_function() -> None:
    """run_forward_simulation convenience function executes from exercise name."""
    result = run_forward_simulation(
        model="gait",
        duration=0.1,
        dt=0.02,
        holding_controller=True,
    )
    assert isinstance(result, ForwardSimulationResult)
    assert result.time[-1] == pytest.approx(0.1)
    assert not result.collapsed
    assert np.all(np.isfinite(result.get_coordinate_values("pelvis_ty")))


@needs_opensim
def test_forward_simulation_with_initial_coordinates() -> None:
    """Initial coordinates are applied to the state before integration."""
    result = run_forward_simulation(
        model="squat",
        duration=0.05,
        dt=0.01,
        initial_coordinates={"hip_r_flex": 0.08},
    )
    hip_vals = result.get_coordinate_values("hip_r_flex")
    assert hip_vals[0] == pytest.approx(0.08, abs=1e-4)


@needs_opensim
def test_forward_simulation_writes_states_file(tmp_path: Path) -> None:
    """When results_dir is provided, states are saved to file."""
    out_dir = tmp_path / "sim_results"
    result = run_forward_simulation(
        model="gait",
        duration=0.05,
        dt=0.01,
        results_dir=out_dir,
    )
    assert result.states_file is not None
    assert result.states_file.is_file()
    content = result.states_file.read_text(encoding="utf-8")
    assert "time\t" in content


@needs_opensim
def test_forward_simulation_input_validation() -> None:
    """Input validation rejects invalid parameters with descriptive errors."""
    with pytest.raises(ValueError, match="duration must be strictly greater"):
        run_forward_simulation("gait", duration=0.0)

    with pytest.raises(ValueError, match="dt must be positive"):
        run_forward_simulation("gait", dt=-0.05)

    with pytest.raises(ValueError, match="not in the model"):
        run_forward_simulation("gait", initial_coordinates={"unknown_coord": 0.5})
