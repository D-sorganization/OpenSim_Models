"""Real-engine inverse dynamics: static standing poses balance gravity."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.tools.inverse_dynamics import (
    InverseDynamicsResult,
    InverseDynamicsTool,
    run_inverse_dynamics,
)

try:
    import opensim
except ImportError:
    opensim = None

needs_opensim = pytest.mark.skipif(
    opensim is None or sys.version_info < (3, 11),
    reason="the opensim pip wheel is published for CPython 3.11+ only",
)

G = 9.80665
BODY_MASS = 80.0


@needs_opensim
def test_static_standing_pose_balances_gravity(tmp_path: Path) -> None:
    """For a static standing pose, root vertical force balances m * g."""
    osim_path = tmp_path / "gait.osim"
    osim_path.write_text(EXERCISE_BUILDERS["gait"](), encoding="utf-8")

    model = opensim.Model(str(osim_path))
    model.initSystem()

    total_mass = sum(
        model.getBodySet().get(i).getMass() for i in range(model.getBodySet().getSize())
    )
    expected_weight = total_mass * G

    times = [i * 0.01 for i in range(10)]
    tool = InverseDynamicsTool(
        model=model,
        times=times,
        excluded_forces="all",
        results_dir=tmp_path / "id_results",
    )
    result = tool.run()

    assert isinstance(result, InverseDynamicsResult)
    assert result.forces_file.is_file()
    assert len(result.time) == len(times)

    ty_forces = result.get_coordinate_force("pelvis_ty")
    assert len(ty_forces) == len(times)
    for fy in ty_forces:
        assert fy == pytest.approx(expected_weight, rel=1e-3)

    tx_forces = result.get_coordinate_force("pelvis_tx")
    tz_forces = result.get_coordinate_force("pelvis_tz")
    for fx in tx_forces:
        assert fx == pytest.approx(0.0, abs=1e-2)
    for fz in tz_forces:
        assert fz == pytest.approx(0.0, abs=1e-2)


@needs_opensim
def test_run_inverse_dynamics_convenience_function(tmp_path: Path) -> None:
    """run_inverse_dynamics convenience function matches InverseDynamicsTool."""
    osim_path = tmp_path / "squat.osim"
    osim_path.write_text(EXERCISE_BUILDERS["squat"](), encoding="utf-8")

    model = opensim.Model(str(osim_path))
    model.initSystem()
    total_mass = sum(
        model.getBodySet().get(i).getMass() for i in range(model.getBodySet().getSize())
    )
    expected_weight = total_mass * G

    times = [i * 0.01 for i in range(10)]
    result = run_inverse_dynamics(
        model=model,
        times=times,
        excluded_forces="all",
        results_dir=tmp_path / "squat_id",
    )

    ty_force = result.forces["pelvis_ty_force"]
    for fy in ty_force:
        assert fy == pytest.approx(expected_weight, rel=1e-3)


@needs_opensim
def test_inverse_dynamics_from_exercise_name(tmp_path: Path) -> None:
    """InverseDynamicsTool accepts exercise name directly."""
    times = [i * 0.01 for i in range(10)]
    result = run_inverse_dynamics(
        model="gait",
        times=times,
        excluded_forces="all",
        results_dir=tmp_path / "gait_named_id",
    )
    ty_force = result.get_coordinate_force("pelvis_ty")
    assert ty_force[0] == pytest.approx(BODY_MASS * G, rel=1e-3)


@needs_opensim
def test_inverse_dynamics_with_coordinates_file(tmp_path: Path) -> None:
    """InverseDynamicsTool executes from a pre-written .sto coordinates file."""
    tool_tmp = InverseDynamicsTool(
        model="gait",
        times=[i * 0.01 for i in range(10)],
        results_dir=tmp_path / "coords_prep",
    )
    coords_file = tool_tmp._create_coordinates_storage(tmp_path)
    assert coords_file.is_file()

    tool = InverseDynamicsTool(
        model="gait",
        coordinates_file=coords_file,
        excluded_forces="all",
        results_dir=tmp_path / "from_file_id",
    )
    result = tool.run()
    assert result.forces_file.is_file()
    assert len(result.time) == 10
    assert result.get_coordinate_force("pelvis_ty")[0] == pytest.approx(
        BODY_MASS * G, rel=1e-3
    )


@needs_opensim
def test_inverse_dynamics_with_custom_coordinates(tmp_path: Path) -> None:
    """InverseDynamicsTool accepts custom coordinate mappings."""
    times = [i * 0.01 for i in range(10)]
    custom_coords = {"pelvis_ty": [0.95] * 10}
    result = run_inverse_dynamics(
        model="gait",
        times=times,
        coordinates=custom_coords,
        excluded_forces="all",
        results_dir=tmp_path / "custom_coords_id",
    )
    assert len(result.time) == 10
    assert result.get_coordinate_force("pelvis_ty")[0] == pytest.approx(
        BODY_MASS * G, rel=1e-3
    )


@needs_opensim
def test_inverse_dynamics_input_validation(tmp_path: Path) -> None:
    """Input validation rejects invalid parameters with descriptive errors."""
    times = [i * 0.01 for i in range(10)]

    # Invalid model
    with pytest.raises(ValueError, match="Model must be an opensim.Model"):
        InverseDynamicsTool(model=12345, times=times)

    # Missing coordinates and times
    with pytest.raises(ValueError, match="Must specify coordinates_file or times"):
        InverseDynamicsTool(model="gait")

    # Non-existent coordinates file
    with pytest.raises(FileNotFoundError, match="Coordinates file not found"):
        InverseDynamicsTool(model="gait", coordinates_file=tmp_path / "missing.sto")

    # Non-existent external loads file
    with pytest.raises(FileNotFoundError, match="External loads file not found"):
        InverseDynamicsTool(
            model="gait",
            times=times,
            external_loads_file=tmp_path / "missing_loads.xml",
        )

    # Invalid time_range
    with pytest.raises(ValueError, match="time_range must be a tuple"):
        InverseDynamicsTool(model="gait", times=times, time_range=(0.5, 0.1))

    with pytest.raises(ValueError, match="time_range must be a tuple"):
        InverseDynamicsTool(model="gait", times=times, time_range=(-0.1, 0.5))

    # Invalid cutoff frequency
    with pytest.raises(ValueError, match="lowpass_cutoff_frequency must be finite"):
        InverseDynamicsTool(
            model="gait", times=times, lowpass_cutoff_frequency=float("nan")
        )

    # Times required when coordinates dict given
    with pytest.raises(ValueError, match="times sequence is required"):
        InverseDynamicsTool(model="gait", coordinates={"pelvis_ty": [0.95]})

    # Too few points (< 6)
    with pytest.raises(ValueError, match="at least 6 points"):
        InverseDynamicsTool(model="gait", times=[0.0, 0.01, 0.02])

    # Times not strictly increasing
    with pytest.raises(ValueError, match="strictly increasing"):
        InverseDynamicsTool(
            model="gait",
            times=[0.0, 0.01, 0.02, 0.03, 0.02, 0.05],
        )

    # Coordinate length mismatch
    with pytest.raises(ValueError, match="does not match times length"):
        InverseDynamicsTool(
            model="gait",
            times=times,
            coordinates={"pelvis_ty": [0.95] * 5},
        )

    # Coordinate not in model
    with pytest.raises(ValueError, match="not in the model"):
        InverseDynamicsTool(
            model="gait",
            times=times,
            coordinates={"non_existent_coord": [0.0] * 10},
        )


@needs_opensim
def test_unknown_coordinate_force_raises_key_error(tmp_path: Path) -> None:
    """get_coordinate_force raises KeyError for unknown coordinate."""
    times = [i * 0.01 for i in range(10)]
    result = run_inverse_dynamics(
        model="gait",
        times=times,
        excluded_forces="all",
        results_dir=tmp_path / "key_error_id",
    )
    with pytest.raises(KeyError, match="not found in results"):
        result.get_coordinate_force("non_existent_coordinate")
