"""Headless recording of a forward-simulation rollout (#471).

:func:`record_rollout` writes a rollout as an OpenSim states file and renders
a stick-figure animation, at parity with the Drake ``recording.py``, MuJoCo
``video.py`` and Pinocchio ``record_rollout`` recorders:

* the coordinate trajectory is written with ``TimeSeriesTable`` /
  ``STOFileAdapter`` to a ``.sto`` file next to the animation, so the OpenSim
  GUI can load it (``File > Load Motion``);
* the animation is drawn with matplotlib's ``Agg`` canvas from body-frame
  origins evaluated through the model at every state (sagittal x-y
  projection), written to MP4 when ``ffmpeg`` is available and to GIF
  otherwise.

No GUI, window or Simbody visualizer is ever started. The stick figure is a
kinematic rendering of the recorded states; it does not by itself qualify the
dynamics.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from opensim_models._messages import ERR_OPENSIM_NOT_INSTALLED
from opensim_models.tools._types import ForwardSimulationResult
from opensim_models.tools._validation import validate_and_load_model

try:
    import opensim
except ImportError:
    opensim = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

Rollout = ForwardSimulationResult | Callable[[Any], ForwardSimulationResult]
"""A simulated trajectory, or a callable ``model -> ForwardSimulationResult``."""

_SUFFIXES = (".mp4", ".gif")

__all__ = ["Rollout", "RolloutRecording", "record_rollout"]


@dataclass(frozen=True)
class RolloutRecording:
    """Result of :func:`record_rollout`.

    Attributes:
        path: The written animation (``.mp4`` or ``.gif``).
        states_path: The written OpenSim ``.sto`` states file.
        frame_count: Number of animation frames (one per recorded state).
        fps: Playback rate in whole frames per second.
        size_bytes: Size of the animation file.
        format: ``"mp4"`` or ``"gif"``; ``gif`` when ffmpeg was unavailable.
        coordinate_count: Number of coordinate columns in the states file.
    """

    path: Path
    states_path: Path
    frame_count: int
    fps: int
    size_bytes: int
    format: str
    coordinate_count: int

    @property
    def duration_s(self) -> float:
        """Playback duration of the animation in seconds."""
        return self.frame_count / self.fps


def record_rollout(
    exercise: Any,
    rollout: Rollout,
    output_path: str | Path,
    *,
    fps: int = 30,
    states_path: str | Path | None = None,
) -> RolloutRecording:
    """Record a forward-simulation rollout headlessly.

    Args:
        exercise: Exercise id (e.g. ``"squat"``), a ``.osim`` path or an
            ``opensim.Model``; used to evaluate body-frame positions.
        rollout: A :class:`ForwardSimulationResult`, or a callable receiving
            a private copy of the model and returning one (for example
            ``lambda m: run_forward_simulation(m, duration=0.5)``).
        output_path: Animation destination, ``.mp4`` or ``.gif``; its parent
            directory must exist. An ``.mp4`` request falls back to a ``.gif``
            file when ffmpeg is unavailable (see ``RolloutRecording.format``).
        fps: Playback rate in whole frames per second (> 0).
        states_path: ``.sto`` destination; defaults to ``output_path`` with a
            ``.sto`` suffix.

    Returns:
        A :class:`RolloutRecording` describing the written artifacts.

    Raises:
        ValueError: Bad ``fps``/paths, empty or non-finite rollout, or
            coordinates not in the model.
        RuntimeError: OpenSim is not installed, or a written file fails its
            postcondition (empty file or wrong frame count).
    """
    if int(fps) != fps or fps <= 0:
        raise ValueError(f"fps must be a positive whole number, got {fps}")
    path = Path(output_path)
    if path.suffix.lower() not in _SUFFIXES:
        raise ValueError(f"output_path must end in one of {_SUFFIXES}, got {path}")
    if not path.parent.is_dir():
        raise ValueError(f"output_path directory does not exist: {path.parent}")
    sto = Path(states_path) if states_path is not None else path.with_suffix(".sto")
    if sto.suffix.lower() != ".sto":
        raise ValueError(f"states_path must end in '.sto', got {sto}")
    if not sto.parent.is_dir():
        raise ValueError(f"states_path directory does not exist: {sto.parent}")
    if opensim is None:
        raise RuntimeError(ERR_OPENSIM_NOT_INSTALLED)

    model = validate_and_load_model(exercise)
    result = rollout(model.clone()) if callable(rollout) else rollout
    names, matrix = _require_trajectory(result, model)

    _write_states(result.time, names, matrix, sto)
    nodes, edges = _stick_figure(model)
    frames = _body_positions(model, names, matrix, nodes)
    out_path, fmt = _render(frames, edges, path, int(fps))

    recording = RolloutRecording(
        path=out_path,
        states_path=sto,
        frame_count=len(frames),
        fps=int(fps),
        size_bytes=out_path.stat().st_size,
        format=fmt,
        coordinate_count=len(names),
    )
    _ensure_recording(recording)
    return recording


def _require_trajectory(
    result: ForwardSimulationResult, model: Any
) -> tuple[list[str], np.ndarray]:
    """Validate the rollout against the model; return ``(names, T x n)``."""
    time = np.asarray(result.time, dtype=float)
    if time.ndim != 1 or time.size == 0:
        raise ValueError("rollout must contain at least one state")
    if not np.all(np.isfinite(time)):
        raise ValueError("rollout time must be finite")
    names = list(result.coordinates)
    if not names:
        raise ValueError("rollout must contain at least one coordinate")
    coord_set = model.getCoordinateSet()
    known = {coord_set.get(i).getName() for i in range(coord_set.getSize())}
    missing = [n for n in names if n not in known]
    if missing:
        raise ValueError(f"rollout coordinates not in model: {missing}")
    columns = []
    for name in names:
        column = np.asarray(result.coordinates[name], dtype=float)
        if column.shape != time.shape:
            raise ValueError(
                f"coordinate {name!r} has shape {column.shape}, expected {time.shape}"
            )
        if not np.all(np.isfinite(column)):
            raise ValueError(f"coordinate {name!r} must be finite")
        columns.append(column)
    return names, np.column_stack(columns)


def _write_states(
    time: np.ndarray, names: list[str], matrix: np.ndarray, path: Path
) -> None:
    """Write coordinate values with ``TimeSeriesTable`` / ``STOFileAdapter``."""
    table = opensim.TimeSeriesTable()
    table.setColumnLabels(opensim.StdVectorString(names))
    for row, t in enumerate(np.asarray(time, dtype=float)):
        table.appendRow(float(t), opensim.RowVector(matrix[row].tolist()))
    # Rotational coordinates are radians, translational metres.
    table.addTableMetaDataString("inDegrees", "no")
    opensim.STOFileAdapter.write(table, str(path))


def _stick_figure(model: Any) -> tuple[list[Any], list[tuple[int, int]]]:
    """Return body-frame nodes and joint edges (parent body -> child body)."""
    model.initSystem()
    bodies = model.getBodySet()
    nodes = [bodies.get(i) for i in range(bodies.getSize())]
    index = {n.getAbsolutePathString(): i for i, n in enumerate(nodes)}
    edges: list[tuple[int, int]] = []
    joints = model.getJointSet()
    for j in range(joints.getSize()):
        joint = joints.get(j)
        parent = joint.getParentFrame().findBaseFrame().getAbsolutePathString()
        child = joint.getChildFrame().findBaseFrame().getAbsolutePathString()
        if parent in index and child in index:  # ground is not drawn
            edges.append((index[parent], index[child]))
    return nodes, edges


def _body_positions(
    model: Any, names: list[str], matrix: np.ndarray, nodes: list[Any]
) -> np.ndarray:
    """Body origins in ground, shape ``(T, n_bodies, 3)``."""
    state = model.initSystem()
    coord_set = model.getCoordinateSet()
    coords = [coord_set.get(n) for n in names]
    frames = np.empty((matrix.shape[0], len(nodes), 3))
    for row, values in enumerate(matrix):
        for coord, value in zip(coords, values, strict=True):
            coord.setValue(state, float(value), False)
        model.realizePosition(state)
        for k, body in enumerate(nodes):
            frames[row, k] = [body.getPositionInGround(state).get(i) for i in range(3)]
    return frames


def _render(
    frames: np.ndarray, edges: list[tuple[int, int]], path: Path, fps: int
) -> tuple[Path, str]:
    """Render the sagittal stick figure with an Agg canvas; return path, format."""
    from matplotlib import animation
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    use_ffmpeg = path.suffix.lower() == ".mp4" and animation.writers.is_available(
        "ffmpeg"
    )
    if use_ffmpeg:
        writer: Any = animation.FFMpegWriter(fps=fps)
        fmt = "mp4"
    else:
        if path.suffix.lower() == ".mp4":
            logger.warning("ffmpeg unavailable; writing GIF instead of %s", path)
            path = path.with_suffix(".gif")
        writer = animation.PillowWriter(fps=fps)
        fmt = "gif"

    xy = frames[:, :, :2]
    lo = xy.reshape(-1, 2).min(axis=0)
    hi = xy.reshape(-1, 2).max(axis=0)
    pad = 0.15 * max(float((hi - lo).max()), 1.0)

    fig = Figure(figsize=(4.0, 4.0), dpi=80)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot()
    ax.set_xlim(lo[0] - pad, hi[0] + pad)
    ax.set_ylim(min(lo[1], 0.0) - pad, hi[1] + pad)
    ax.set_aspect("equal")
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.axhline(0.0, color="0.6", lw=1.0)
    lines = [ax.plot([], [], "o-", color="C0", lw=2.0, ms=3.0)[0] for _ in edges]
    title = ax.set_title("")

    with writer.saving(fig, str(path), dpi=80):
        for t, pts in enumerate(xy):
            for line, (a, b) in zip(lines, edges, strict=True):
                line.set_data([pts[a, 0], pts[b, 0]], [pts[a, 1], pts[b, 1]])
            title.set_text(f"frame {t + 1}/{len(xy)}")
            writer.grab_frame()
    return path, fmt


def _ensure_recording(recording: RolloutRecording) -> None:
    """Postconditions: non-empty files and the expected GIF frame count."""
    if recording.size_bytes <= 0:
        raise RuntimeError(f"recording {recording.path} is empty")
    if recording.states_path.stat().st_size <= 0:
        raise RuntimeError(f"states file {recording.states_path} is empty")
    if recording.format == "gif":
        from PIL import Image

        with Image.open(recording.path) as img:
            stored = int(getattr(img, "n_frames", 1))
        if stored != recording.frame_count:
            raise RuntimeError(
                f"recording {recording.path} stores {stored} frames, "
                f"expected {recording.frame_count}"
            )
