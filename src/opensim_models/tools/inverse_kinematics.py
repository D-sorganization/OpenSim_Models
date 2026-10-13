"""Public wrapper around OpenSim's InverseKinematicsTool with input validation.

Design-by-Contract: all inputs are validated before execution.
Results are parsed into structured dataclasses with numpy arrays.
Rotational coordinate values are returned in radians by default (SI convention).
"""

from __future__ import annotations

import logging
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from opensim_models._messages import (
    ERR_IK_TOOL_RUN_FAILED,
    ERR_MARKER_FILE_NOT_FOUND,
    ERR_MODEL_HAS_NO_MARKERS,
    ERR_NO_MARKERS_SPECIFIED,
    ERR_OPENSIM_NOT_INSTALLED,
)
from opensim_models.tools._trc import write_trc_file
from opensim_models.tools._types import InverseKinematicsResult
from opensim_models.tools._validation import (
    validate_and_load_model,
    validate_file,
    validate_ik_times,
    validate_marker_trajectories,
    validate_marker_weights,
    validate_time_range,
)

try:
    import opensim
except ImportError:
    opensim = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

__all__ = [
    "InverseKinematicsResult",
    "InverseKinematicsTool",
    "run_inverse_kinematics",
    "write_trc_file",
]


class InverseKinematicsTool:
    """Validated wrapper for OpenSim's InverseKinematicsTool."""

    def __init__(
        self,
        model: Any,
        marker_file: str | Path | None = None,
        *,
        marker_trajectories: Mapping[str, Sequence[Sequence[float]]] | None = None,
        marker_weights: Mapping[str, float] | None = None,
        times: Sequence[float] | None = None,
        time_range: tuple[float, float] | None = None,
        results_dir: str | Path | None = None,
        output_motion_file: str = "inverse_kinematics.mot",
        report_errors: bool = False,
        report_marker_locations: bool = False,
        constraint_weight: float = 20.0,
        accuracy: float = 1e-5,
    ) -> None:
        if opensim is None:
            raise RuntimeError(ERR_OPENSIM_NOT_INSTALLED)

        self._model = validate_and_load_model(model)
        marker_set = self._model.getMarkerSet()
        if marker_set.getSize() == 0:
            raise ValueError(ERR_MODEL_HAS_NO_MARKERS)
        self._model_marker_names = {
            marker_set.get(i).getName() for i in range(marker_set.getSize())
        }

        self._marker_file = validate_file(marker_file, ERR_MARKER_FILE_NOT_FOUND)
        self._times = validate_ik_times(times, marker_trajectories)
        self._marker_trajectories = validate_marker_trajectories(
            marker_trajectories, self._times, self._model_marker_names
        )

        if self._marker_file is None and self._marker_trajectories is None:
            raise ValueError(ERR_NO_MARKERS_SPECIFIED)

        self._marker_weights = (
            validate_marker_weights(marker_weights, self._model_marker_names) or {}
        )
        self._time_range = validate_time_range(time_range)

        self._results_dir = Path(results_dir) if results_dir is not None else None
        self._output_file = (
            output_motion_file
            if output_motion_file.endswith((".mot", ".sto"))
            else f"{output_motion_file}.mot"
        )
        self._report_errors = report_errors
        self._report_marker_locations = report_marker_locations
        self._constraint_weight = float(constraint_weight)
        self._accuracy = float(accuracy)

    def _create_trc_storage(self, tmp_dir: Path) -> Path:
        assert self._times is not None
        assert self._marker_trajectories is not None
        trc_file = tmp_dir / "input_markers.trc"
        return write_trc_file(
            trc_file, self._times, self._marker_trajectories, units="m"
        )

    def _configure_tool(self, tool: Any, marker_path: Path, work_dir: Path) -> None:
        out_path = work_dir / self._output_file
        tool.setModel(self._model)
        tool.setMarkerDataFileName(str(marker_path))
        tool.setOutputMotionFileName(str(out_path))
        tool.setResultsDir(str(work_dir))
        tool.set_report_errors(self._report_errors)
        tool.set_report_marker_locations(self._report_marker_locations)
        tool.set_constraint_weight(self._constraint_weight)
        tool.set_accuracy(self._accuracy)

        if self._time_range is not None:
            tool.setStartTime(self._time_range[0])
            tool.setEndTime(self._time_range[1])
        elif self._times is not None:
            tool.setStartTime(self._times[0])
            tool.setEndTime(self._times[-1])

        task_set = getattr(tool, "getIKTaskSet", None)
        task_set = task_set() if task_set is not None else tool.get_IKTaskSet()
        if task_set.getSize() == 0:
            for name in sorted(self._model_marker_names):
                task = opensim.IKMarkerTask()
                task.setName(name)
                weight = self._marker_weights.get(name, 1.0)
                task.setWeight(weight)
                task.setApply(weight > 0.0)
                if hasattr(task_set, "cloneAndAppend"):
                    task_set.cloneAndAppend(task)
                else:
                    task_set.adoptAndAppend(task)
        else:
            for i in range(task_set.getSize()):
                task = task_set.get(i)
                m_task = opensim.IKMarkerTask.safeDownCast(task)
                if m_task and m_task.getName() in self._marker_weights:
                    w = self._marker_weights[m_task.getName()]
                    m_task.setWeight(w)
                    m_task.setApply(w > 0.0)

    def _is_rotational_coord(self, coord_name: str) -> bool:
        coord_set = self._model.getCoordinateSet()
        if coord_set.getIndex(coord_name) != -1:
            coord = coord_set.get(coord_name)
            try:
                trans_type = opensim.Coordinate.MotionType_Translational
                return bool(coord.getMotionType() != trans_type)
            except AttributeError:
                pass
        return not coord_name.endswith(("_tx", "_ty", "_tz"))

    def _parse_results(self, out_path: Path) -> InverseKinematicsResult:
        if not out_path.is_file():
            candidates = [
                out_path.parent / self._output_file,
                out_path.parent / Path(self._output_file).name,
                Path(self._output_file),
                Path(Path(self._output_file).name),
            ]
            for cand in candidates:
                if cand.is_file():
                    out_path = cand
                    break
        if not out_path.is_file():
            raise FileNotFoundError(f"Expected output file not written: {out_path}")

        storage = opensim.Storage(str(out_path))
        raw_labels = storage.getColumnLabels()
        labels = [raw_labels.get(i) for i in range(raw_labels.getSize())]

        num_rows = storage.getSize()
        num_cols = len(labels) - 1
        time_vals = np.zeros(num_rows, dtype=float)
        coord_matrix = np.zeros((num_rows, num_cols), dtype=float)

        for r in range(num_rows):
            sv = storage.getStateVector(r)
            time_vals[r] = sv.getTime()
            data = sv.getData()
            for c in range(num_cols):
                coord_matrix[r, c] = data.get(c)

        is_degrees = getattr(storage, "isInDegrees", lambda: True)()

        coords_dict: dict[str, np.ndarray] = {}
        for c in range(num_cols):
            name = labels[c + 1]
            col_data = coord_matrix[:, c]
            if is_degrees and self._is_rotational_coord(name):
                coords_dict[name] = np.deg2rad(col_data)
            else:
                coords_dict[name] = col_data.copy()

        return InverseKinematicsResult(
            motion_file=out_path,
            time=time_vals,
            coordinates=coords_dict,
            column_labels=labels,
            in_degrees=is_degrees,
        )

    def run(self) -> InverseKinematicsResult:
        """Execute inverse kinematics and return solved coordinate trajectory."""
        if self._results_dir is not None:
            work_dir = self._results_dir
            work_dir.mkdir(parents=True, exist_ok=True)
        else:
            work_dir = Path(tempfile.mkdtemp(prefix="opensim_ik_"))

        marker_path = (
            self._marker_file
            if self._marker_file is not None
            else self._create_trc_storage(work_dir)
        )

        tool = opensim.InverseKinematicsTool()
        self._configure_tool(tool, marker_path, work_dir)

        if not tool.run():
            raise RuntimeError(ERR_IK_TOOL_RUN_FAILED)

        return self._parse_results(work_dir / self._output_file)


def run_inverse_kinematics(
    model: Any,
    marker_file: str | Path | None = None,
    *,
    marker_trajectories: Mapping[str, Sequence[Sequence[float]]] | None = None,
    marker_weights: Mapping[str, float] | None = None,
    times: Sequence[float] | None = None,
    time_range: tuple[float, float] | None = None,
    results_dir: str | Path | None = None,
    output_motion_file: str = "inverse_kinematics.mot",
    report_errors: bool = False,
    report_marker_locations: bool = False,
    constraint_weight: float = 20.0,
    accuracy: float = 1e-5,
) -> InverseKinematicsResult:
    """Run OpenSim inverse kinematics and return structured results."""
    tool = InverseKinematicsTool(
        model=model,
        marker_file=marker_file,
        marker_trajectories=marker_trajectories,
        marker_weights=marker_weights,
        times=times,
        time_range=time_range,
        results_dir=results_dir,
        output_motion_file=output_motion_file,
        report_errors=report_errors,
        report_marker_locations=report_marker_locations,
        constraint_weight=constraint_weight,
        accuracy=accuracy,
    )
    return tool.run()
