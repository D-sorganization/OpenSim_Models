"""Public forward dynamics simulation API using OpenSim Manager and actuators.

Provides feedback/holding control, coordinate actuator integration,
and forward simulation rollouts with Design-by-Contract preconditions.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from opensim_models._messages import (
    ERR_ACCURACY_POSITIVE,
    ERR_COLLAPSE_THRESHOLD_FINITE,
    ERR_COORDINATE_NOT_IN_MODEL,
    ERR_DT_POSITIVE,
    ERR_DURATION_POSITIVE,
    ERR_OPENSIM_NOT_INSTALLED,
    ERR_OPTIMAL_FORCE_POSITIVE,
    ERR_SIMULATION_BLOWN_UP,
)
from opensim_models.tools._types import ForwardSimulationResult
from opensim_models.tools._validation import validate_and_load_model

try:
    import opensim
except ImportError:
    opensim = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

__all__ = [
    "ForwardSimulationResult",
    "ForwardSimulationTool",
    "add_coordinate_actuators",
    "run_forward_simulation",
]


def _has_coord(coord_set: Any, name: str) -> bool:
    if hasattr(coord_set, "getIndex"):
        return bool(coord_set.getIndex(name) != -1)
    return bool(getattr(coord_set, "hasComponent", lambda _: True)(name))


def add_coordinate_actuators(
    model: Any,
    optimal_force: float = 1000.0,
    coordinates: Sequence[str] | None = None,
) -> list[str]:
    """Add CoordinateActuator to model coordinates."""
    if opensim is None:
        raise RuntimeError(ERR_OPENSIM_NOT_INSTALLED)
    if not math.isfinite(optimal_force) or optimal_force <= 0:
        raise ValueError(ERR_OPTIMAL_FORCE_POSITIVE.format(value=optimal_force))

    coord_set = model.getCoordinateSet()
    existing_actuators = {
        model.getActuators().get(i).getName()
        for i in range(model.getActuators().getSize())
    }

    if coordinates is not None:
        target_names = list(coordinates)
    else:
        target_names = [
            coord_set.get(i).getName()
            for i in range(coord_set.getSize())
            if not coord_set.get(i).getName().startswith("pelvis_t")
        ]

    added: list[str] = []
    for name in target_names:
        act_name = f"{name}_actuator"
        if act_name in existing_actuators:
            continue
        if not _has_coord(coord_set, name):
            raise ValueError(ERR_COORDINATE_NOT_IN_MODEL.format(name=name))

        coord = coord_set.get(name)
        actuator = opensim.CoordinateActuator()
        actuator.setCoordinate(coord)
        actuator.setName(act_name)
        actuator.setOptimalForce(float(optimal_force))
        model.addForce(actuator)
        added.append(act_name)

    return added


class ForwardSimulationTool:
    """Configurable forward dynamics simulator using OpenSim Manager and actuators."""

    def __init__(
        self,
        model: Any,
        *,
        duration: float = 0.5,
        initial_time: float = 0.0,
        dt: float = 0.01,
        holding_controller: bool = True,
        holding_controls: Mapping[str, float] | None = None,
        actuator_optimal_force: float = 1000.0,
        actuated_coordinates: Sequence[str] | None = None,
        initial_coordinates: Mapping[str, float] | None = None,
        initial_speeds: Mapping[str, float] | None = None,
        accuracy: float = 1e-4,
        collapse_threshold: float = 0.5,
        results_dir: str | Path | None = None,
        output_states_file: str = "forward_simulation_states.sto",
    ) -> None:
        if opensim is None:
            raise RuntimeError(ERR_OPENSIM_NOT_INSTALLED)

        if not math.isfinite(duration) or duration <= initial_time:
            raise ValueError(
                ERR_DURATION_POSITIVE.format(
                    duration=duration, initial_time=initial_time
                )
            )
        if not math.isfinite(dt) or dt <= 0 or dt > (duration - initial_time):
            raise ValueError(ERR_DT_POSITIVE.format(dt=dt))
        if not math.isfinite(accuracy) or accuracy <= 0:
            raise ValueError(ERR_ACCURACY_POSITIVE.format(value=accuracy))
        if not math.isfinite(collapse_threshold):
            raise ValueError(
                ERR_COLLAPSE_THRESHOLD_FINITE.format(value=collapse_threshold)
            )

        self._model = validate_and_load_model(model)
        self._duration = float(duration)
        self._initial_time = float(initial_time)
        self._dt = float(dt)
        self._holding_controller = bool(holding_controller)
        self._holding_controls = dict(holding_controls) if holding_controls else {}
        self._actuator_optimal_force = float(actuator_optimal_force)
        self._actuated_coordinates = actuated_coordinates
        self._initial_coordinates = initial_coordinates
        self._initial_speeds = initial_speeds
        self._accuracy = float(accuracy)
        self._collapse_threshold = float(collapse_threshold)
        self._results_dir = Path(results_dir) if results_dir is not None else None
        self._output_file = output_states_file

    def _setup_actuators_and_controller(self) -> None:
        added_acts = add_coordinate_actuators(
            self._model,
            optimal_force=self._actuator_optimal_force,
            coordinates=self._actuated_coordinates,
        )
        if self._holding_controller and (
            added_acts or self._model.getActuators().getSize() > 0
        ):
            controller = opensim.PrescribedController()
            controller.setName("holding_controller")
            actuators = self._model.getActuators()
            for i in range(actuators.getSize()):
                act = actuators.get(i)
                controller.addActuator(act)
                val = float(self._holding_controls.get(act.getName(), 0.0))
                controller.prescribeControlForActuator(
                    act.getName(), opensim.Constant(val)
                )
            self._model.addController(controller)

    def _apply_initial_pose(self, state: Any) -> None:
        coord_set = self._model.getCoordinateSet()
        if self._initial_coordinates:
            for name, val in self._initial_coordinates.items():
                if not _has_coord(coord_set, name):
                    raise ValueError(ERR_COORDINATE_NOT_IN_MODEL.format(name=name))
                coord_set.get(name).setValue(state, float(val))
        if self._initial_speeds:
            for name, spd in self._initial_speeds.items():
                if not _has_coord(coord_set, name):
                    raise ValueError(ERR_COORDINATE_NOT_IN_MODEL.format(name=name))
                coord_set.get(name).setSpeedValue(state, float(spd))
        self._model.realizePosition(state)

    def run(self) -> ForwardSimulationResult:
        """Run forward simulation and return recorded trajectory."""
        self._setup_actuators_and_controller()
        state = self._model.initSystem()
        state.setTime(self._initial_time)
        self._apply_initial_pose(state)

        coord_set = self._model.getCoordinateSet()
        coord_names = [coord_set.get(i).getName() for i in range(coord_set.getSize())]

        num_steps = max(1, int(round((self._duration - self._initial_time) / self._dt)))
        time_points = [
            self._initial_time + i * self._dt for i in range(1, num_steps + 1)
        ]
        if time_points[-1] < self._duration - 1e-9:
            time_points.append(self._duration)

        recorded_times = [self._initial_time]
        recorded_coords: dict[str, list[float]] = {
            n: [coord_set.get(n).getValue(state)] for n in coord_names
        }
        recorded_speeds: dict[str, list[float]] = {
            n: [coord_set.get(n).getSpeedValue(state)] for n in coord_names
        }

        manager = opensim.Manager(self._model)
        manager.setIntegratorAccuracy(self._accuracy)
        manager.initialize(state)

        for t in time_points:
            state = manager.integrate(float(t))
            cur_t = float(state.getTime())
            recorded_times.append(cur_t)
            for n in coord_names:
                coord = coord_set.get(n)
                c_val = float(coord.getValue(state))
                s_val = float(coord.getSpeedValue(state))
                if not (math.isfinite(c_val) and math.isfinite(s_val)):
                    raise RuntimeError(ERR_SIMULATION_BLOWN_UP)
                recorded_coords[n].append(c_val)
                recorded_speeds[n].append(s_val)

        coords_arr = {k: np.array(v, dtype=float) for k, v in recorded_coords.items()}
        speeds_arr = {k: np.array(v, dtype=float) for k, v in recorded_speeds.items()}
        time_arr = np.array(recorded_times, dtype=float)

        # Evaluate minimum pelvis height
        if "pelvis_ty" in coords_arr:
            min_pelvis_height = float(np.min(coords_arr["pelvis_ty"]))
        else:
            min_pelvis_height = 1.0
        collapsed = min_pelvis_height < self._collapse_threshold

        states_file: Path | None = None
        if self._results_dir is not None:
            self._results_dir.mkdir(parents=True, exist_ok=True)
            states_file = self._results_dir / self._output_file
            lines = ["time\t" + "\t".join(coord_names)]
            for r in range(len(time_arr)):
                row = [f"{time_arr[r]:.6f}"] + [
                    f"{coords_arr[n][r]:.6f}" for n in coord_names
                ]
                lines.append("\t".join(row))
            states_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        return ForwardSimulationResult(
            time=time_arr,
            coordinates=coords_arr,
            speeds=speeds_arr,
            min_pelvis_height=min_pelvis_height,
            collapsed=collapsed,
            states_file=states_file,
            column_labels=["time"] + coord_names,
        )


def run_forward_simulation(
    model: Any,
    *,
    duration: float = 0.5,
    initial_time: float = 0.0,
    dt: float = 0.01,
    holding_controller: bool = True,
    holding_controls: Mapping[str, float] | None = None,
    actuator_optimal_force: float = 1000.0,
    actuated_coordinates: Sequence[str] | None = None,
    initial_coordinates: Mapping[str, float] | None = None,
    initial_speeds: Mapping[str, float] | None = None,
    accuracy: float = 1e-4,
    collapse_threshold: float = 0.5,
    results_dir: str | Path | None = None,
    output_states_file: str = "forward_simulation_states.sto",
) -> ForwardSimulationResult:
    """Run forward dynamics simulation and return structured rollout trajectory."""
    tool = ForwardSimulationTool(
        model=model,
        duration=duration,
        initial_time=initial_time,
        dt=dt,
        holding_controller=holding_controller,
        holding_controls=holding_controls,
        actuator_optimal_force=actuator_optimal_force,
        actuated_coordinates=actuated_coordinates,
        initial_coordinates=initial_coordinates,
        initial_speeds=initial_speeds,
        accuracy=accuracy,
        collapse_threshold=collapse_threshold,
        results_dir=results_dir,
        output_states_file=output_states_file,
    )
    return tool.run()
