"""Headless rollout recording: .sto states plus a rendered animation (#471)."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from opensim_models.tools.recording import (  # noqa: E402
    RolloutRecording,
    record_rollout,
)

try:
    import opensim
except ImportError:
    opensim = None

needs_opensim = pytest.mark.skipif(
    opensim is None,
    reason="opensim is not installed in this Python environment",
)


def _short_squat_rollout(model: object):
    from opensim_models.tools.forward_simulation import run_forward_simulation

    return run_forward_simulation(model, duration=0.1, dt=0.02)


@needs_opensim
def test_record_squat_rollout_writes_states_and_animation(tmp_path: Path) -> None:
    recording = record_rollout(
        "squat", _short_squat_rollout, tmp_path / "squat.gif", fps=10
    )

    assert isinstance(recording, RolloutRecording)
    assert recording.path.is_file()
    assert recording.size_bytes > 0
    assert recording.path.stat().st_size == recording.size_bytes
    assert recording.frame_count == 6  # initial state + 5 steps
    assert recording.fps == 10

    from PIL import Image

    with Image.open(recording.path) as img:
        assert img.n_frames == recording.frame_count

    table = opensim.TimeSeriesTable(str(recording.states_path))
    assert table.getNumRows() == recording.frame_count
    labels = list(table.getColumnLabels())
    assert len(labels) == recording.coordinate_count
    assert "pelvis_ty" in labels
    assert table.getNumColumns() == len(labels)


@needs_opensim
def test_mp4_request_without_ffmpeg_falls_back_to_gif(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from matplotlib import animation

    monkeypatch.setattr(
        animation.writers, "is_available", lambda name: name != "ffmpeg"
    )
    recording = record_rollout(
        "squat", _short_squat_rollout, tmp_path / "squat.mp4", fps=10
    )
    assert recording.format == "gif"
    assert recording.path.suffix == ".gif"
    assert recording.path.is_file()


@needs_opensim
def test_accepts_precomputed_result(tmp_path: Path) -> None:
    result = _short_squat_rollout("squat")
    recording = record_rollout("squat", result, tmp_path / "a.gif")
    assert recording.frame_count == len(result.time)


def test_rejects_bad_arguments(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="fps"):
        record_rollout("squat", lambda m: None, tmp_path / "a.gif", fps=0)
    with pytest.raises(ValueError, match="output_path"):
        record_rollout("squat", lambda m: None, tmp_path / "a.avi")
    with pytest.raises(ValueError, match="directory"):
        record_rollout("squat", lambda m: None, tmp_path / "nope" / "a.gif")


@needs_opensim
def test_rejects_non_finite_rollout(tmp_path: Path) -> None:
    result = _short_squat_rollout("squat")
    bad = {k: v.copy() for k, v in result.coordinates.items()}
    bad["pelvis_ty"][2] = np.nan
    from dataclasses import replace

    with pytest.raises(ValueError, match="finite"):
        record_rollout("squat", replace(result, coordinates=bad), tmp_path / "a.gif")
