"""Input validation and loading helpers for tool execution."""

from __future__ import annotations

import math
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from opensim_models._messages import (
    ERR_COORDINATE_LENGTH_MISMATCH,
    ERR_COORDINATE_NOT_IN_MODEL,
    ERR_INVALID_MODEL,
    ERR_INVALID_TIME_RANGE,
    ERR_LOWPASS_CUTOFF_FINITE,
    ERR_TIMES_NOT_INCREASING,
    ERR_TIMES_REQUIRED,
    ERR_TIMES_TOO_SHORT,
)
from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.shared.contracts.preconditions import require_finite

try:
    import opensim
except ImportError:
    opensim = None  # type: ignore[assignment]


def validate_and_load_model(model: Any) -> Any:
    """Validate and return an opensim.Model instance."""
    if opensim is not None and isinstance(model, opensim.Model):
        return model
    if isinstance(model, str) and model in EXERCISE_BUILDERS:
        with tempfile.TemporaryDirectory(prefix="opensim_id_model_") as tmp:
            model_path = Path(tmp) / f"{model}.osim"
            model_path.write_text(EXERCISE_BUILDERS[model](), encoding="utf-8")
            return opensim.Model(str(model_path))
    if isinstance(model, (str, Path)):
        path = Path(model)
        if not path.is_file():
            raise FileNotFoundError(f"Model file not found: {path}")
        return opensim.Model(str(path))
    raise ValueError(ERR_INVALID_MODEL.format(model=model))


def validate_file(path: str | Path | None, err_template: str) -> Path | None:
    """Validate that *path* exists as a file if given."""
    if path is None:
        return None
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(err_template.format(path=p))
    return p


def validate_times(
    times: Sequence[float] | None,
    coordinates: Mapping[str, Sequence[float]] | None,
) -> list[float] | None:
    """Validate strictly increasing times sequence with >= 6 points."""
    if times is None:
        if coordinates is not None:
            raise ValueError(ERR_TIMES_REQUIRED)
        return None
    if len(times) < 6:
        raise ValueError(ERR_TIMES_TOO_SHORT.format(count=len(times)))
    require_finite(times, "times")
    for i in range(1, len(times)):
        if times[i] <= times[i - 1]:
            raise ValueError(ERR_TIMES_NOT_INCREASING)
    return [float(t) for t in times]


def validate_coordinates(
    coords: Mapping[str, Sequence[float]] | None,
    times: list[float] | None,
    coord_names: set[str],
) -> dict[str, list[float]] | None:
    """Validate coordinates mapping against model coordinates and times length."""
    if coords is None:
        return None
    assert times is not None
    out: dict[str, list[float]] = {}
    for name, vals in coords.items():
        if name not in coord_names:
            raise ValueError(ERR_COORDINATE_NOT_IN_MODEL.format(name=name))
        if len(vals) != len(times):
            raise ValueError(
                ERR_COORDINATE_LENGTH_MISMATCH.format(
                    name=name, length=len(vals), expected=len(times)
                )
            )
        require_finite(vals, f"coordinate {name}")
        out[name] = [float(v) for v in vals]
    return out


def validate_time_range(
    tr: tuple[float, float] | None,
) -> tuple[float, float] | None:
    """Validate start and end time range."""
    if tr is None:
        return None
    if (
        not isinstance(tr, (tuple, list))
        or len(tr) != 2
        or not math.isfinite(tr[0])
        or not math.isfinite(tr[1])
        or tr[0] < 0
        or tr[0] > tr[1]
    ):
        raise ValueError(ERR_INVALID_TIME_RANGE.format(value=tr))
    return (float(tr[0]), float(tr[1]))


def validate_lowpass_cutoff(freq: float) -> float:
    """Validate lowpass cutoff frequency is finite."""
    if not math.isfinite(freq):
        raise ValueError(ERR_LOWPASS_CUTOFF_FINITE.format(value=freq))
    return float(freq)


def resolve_excluded_forces(
    model: Any, excluded: Sequence[str] | str | None
) -> list[str] | None:
    """Resolve excluded forces list or 'all' shortcut."""
    if excluded == "all":
        forces = model.getForceSet()
        return [forces.get(i).getName() for i in range(forces.getSize())]
    if excluded is not None:
        return [str(f) for f in excluded]
    return None
