"""Public wrapper around OpenSim's InverseDynamicsTool with input validation.

Design-by-Contract: all inputs are validated before execution.
Results are parsed into structured dataclasses with numpy arrays.
"""

from __future__ import annotations

import logging
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from opensim_models._messages import (
    ERR_COORDINATES_FILE_NOT_FOUND,
    ERR_EXTERNAL_LOADS_FILE_NOT_FOUND,
    ERR_ID_TOOL_RUN_FAILED,
    ERR_NO_COORDINATES_SPECIFIED,
    ERR_OPENSIM_NOT_INSTALLED,
)
from opensim_models.tools._types import InverseDynamicsResult
from opensim_models.tools._validation import (
    resolve_excluded_forces,
    validate_and_load_model,
    validate_coordinates,
    validate_file,
    validate_lowpass_cutoff,
    validate_time_range,
    validate_times,
)

try:
    import opensim
except ImportError:
    opensim = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

__all__ = ["InverseDynamicsResult", "InverseDynamicsTool", "run_inverse_dynamics"]


class InverseDynamicsTool:
    """Validated wrapper for OpenSim's InverseDynamicsTool."""

    def __init__(
        self,
        model: Any,
        coordinates_file: str | Path | None = None,
        *,
        coordinates: Mapping[str, Sequence[float]] | None = None,
        times: Sequence[float] | None = None,
        time_range: tuple[float, float] | None = None,
        lowpass_cutoff_frequency: float = -1.0,
        excluded_forces: Sequence[str] | str | None = None,
        external_loads_file: str | Path | None = None,
        results_dir: str | Path | None = None,
        output_gen_force_file: str = "inverse_dynamics.sto",
    ) -> None:
        if opensim is None:
            raise RuntimeError(ERR_OPENSIM_NOT_INSTALLED)

        self._model = validate_and_load_model(model)
        coord_set = self._model.getCoordinateSet()
        self._coord_names = {
            coord_set.get(i).getName() for i in range(coord_set.getSize())
        }

        self._coordinates_file = validate_file(
            coordinates_file, ERR_COORDINATES_FILE_NOT_FOUND
        )
        self._times = validate_times(times, coordinates)
        self._coordinates = validate_coordinates(
            coordinates, self._times, self._coord_names
        )

        if self._coordinates_file is None and self._times is None:
            raise ValueError(ERR_NO_COORDINATES_SPECIFIED)

        self._time_range = validate_time_range(time_range)
        self._lowpass_cutoff = validate_lowpass_cutoff(lowpass_cutoff_frequency)
        self._external_loads_file = validate_file(
            external_loads_file, ERR_EXTERNAL_LOADS_FILE_NOT_FOUND
        )
        self._excluded_forces = resolve_excluded_forces(self._model, excluded_forces)

        self._results_dir = Path(results_dir) if results_dir is not None else None
        self._output_file = (
            output_gen_force_file
            if output_gen_force_file.endswith(".sto")
            else f"{output_gen_force_file}.sto"
        )

    def _create_coordinates_storage(self, tmp_dir: Path) -> Path:
        assert self._times is not None
        state = self._model.initSystem()
        coord_set = self._model.getCoordinateSet()
        coord_list = [coord_set.get(i).getName() for i in range(coord_set.getSize())]

        labels = opensim.ArrayStr()
        labels.append("time")
        for name in coord_list:
            labels.append(name)

        storage = opensim.Storage()
        storage.setColumnLabels(labels)
        storage.setName("coordinates")

        custom_coords = self._coordinates or {}
        for t_idx, t in enumerate(self._times):
            vec = opensim.Vector(len(coord_list), 0.0)
            for c_idx, c_name in enumerate(coord_list):
                val = (
                    custom_coords[c_name][t_idx]
                    if c_name in custom_coords
                    else coord_set.get(c_name).getValue(state)
                )
                vec.set(c_idx, val)
            storage.append(t, vec)

        storage_file = tmp_dir / "input_coordinates.sto"
        storage.printResult(storage, "input_coordinates", str(tmp_dir), 0.0, ".sto")
        return storage_file

    def _configure_tool(self, tool: Any, coords_path: Path, work_dir: Path) -> None:
        tool.setModel(self._model)
        tool.setCoordinatesFileName(str(coords_path))
        tool.setLowpassCutoffFrequency(self._lowpass_cutoff)
        tool.setOutputGenForceFileName(self._output_file)
        tool.setResultsDir(str(work_dir))

        if self._time_range is not None:
            tool.setStartTime(self._time_range[0])
            tool.setEndTime(self._time_range[1])
        elif self._times is not None:
            tool.setStartTime(self._times[0])
            tool.setEndTime(self._times[-1])

        if self._excluded_forces:
            arr = opensim.ArrayStr()
            for force_name in self._excluded_forces:
                arr.append(force_name)
            tool.setExcludedForces(arr)

        if self._external_loads_file is not None:
            tool.setExternalLoadsFileName(str(self._external_loads_file))

    def _parse_results(self, out_path: Path) -> InverseDynamicsResult:
        if not out_path.is_file():
            raise FileNotFoundError(f"Expected output file not written: {out_path}")

        storage = opensim.Storage(str(out_path))
        raw_labels = storage.getColumnLabels()
        labels = [raw_labels.get(i) for i in range(raw_labels.getSize())]

        num_rows = storage.getSize()
        num_cols = len(labels) - 1
        time_vals = np.zeros(num_rows, dtype=float)
        force_matrix = np.zeros((num_rows, num_cols), dtype=float)

        for r in range(num_rows):
            sv = storage.getStateVector(r)
            time_vals[r] = sv.getTime()
            data = sv.getData()
            for c in range(num_cols):
                force_matrix[r, c] = data.get(c)

        forces_dict: dict[str, np.ndarray] = {
            labels[c + 1]: force_matrix[:, c] for c in range(num_cols)
        }
        return InverseDynamicsResult(
            forces_file=out_path,
            time=time_vals,
            forces=forces_dict,
            column_labels=labels,
        )

    def run(self) -> InverseDynamicsResult:
        """Execute inverse dynamics and return structured forces."""
        if self._results_dir is not None:
            work_dir = self._results_dir
            work_dir.mkdir(parents=True, exist_ok=True)
        else:
            work_dir = Path(tempfile.mkdtemp(prefix="opensim_id_"))

        coords_path = (
            self._coordinates_file
            if self._coordinates_file is not None
            else self._create_coordinates_storage(work_dir)
        )

        tool = opensim.InverseDynamicsTool()
        self._configure_tool(tool, coords_path, work_dir)

        if not tool.run():
            raise RuntimeError(ERR_ID_TOOL_RUN_FAILED)

        return self._parse_results(work_dir / self._output_file)


def run_inverse_dynamics(
    model: Any,
    coordinates_file: str | Path | None = None,
    *,
    coordinates: Mapping[str, Sequence[float]] | None = None,
    times: Sequence[float] | None = None,
    time_range: tuple[float, float] | None = None,
    lowpass_cutoff_frequency: float = -1.0,
    excluded_forces: Sequence[str] | str | None = None,
    external_loads_file: str | Path | None = None,
    results_dir: str | Path | None = None,
    output_gen_force_file: str = "inverse_dynamics.sto",
) -> InverseDynamicsResult:
    """Run OpenSim inverse dynamics and return structured results."""
    tool = InverseDynamicsTool(
        model=model,
        coordinates_file=coordinates_file,
        coordinates=coordinates,
        times=times,
        time_range=time_range,
        lowpass_cutoff_frequency=lowpass_cutoff_frequency,
        excluded_forces=excluded_forces,
        external_loads_file=external_loads_file,
        results_dir=results_dir,
        output_gen_force_file=output_gen_force_file,
    )
    return tool.run()
