# SPDX-License-Identifier: MIT
"""Real-engine OpenSim test for MarkerSet (#387)."""

from __future__ import annotations

from pathlib import Path

import pytest

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.model_pack import list_exercises

try:
    import opensim

    HAS_OPENSIM = True
except ImportError:
    HAS_OPENSIM = False

needs_opensim = pytest.mark.skipif(
    not HAS_OPENSIM,
    reason="opensim is not installed in this Python environment",
)

EXERCISES = list_exercises()
BARBELL_EXERCISES = ("squat", "deadlift", "bench_press", "snatch", "clean_and_jerk")


@needs_opensim
@pytest.mark.parametrize("exercise", EXERCISES)
def test_markerset_loads_and_initializes_in_real_opensim(
    tmp_path: Path, exercise: str
) -> None:
    """OpenSim loads the model XML, initializes the system, and queries the MarkerSet."""
    path = tmp_path / f"{exercise}.osim"
    path.write_text(EXERCISE_BUILDERS[exercise](), encoding="utf-8")

    model = opensim.Model(str(path))
    model.initSystem()

    marker_set = model.getMarkerSet()
    assert marker_set.getSize() >= 15, (
        f"{exercise} marker set has {marker_set.getSize()} markers, expected at least 15"
    )

    # Check key markers can be resolved
    assert marker_set.get("pelvis") is not None
    assert marker_set.get("torso") is not None
    assert marker_set.get("head") is not None

    if exercise in BARBELL_EXERCISES:
        bar_marker = (
            marker_set.get("bar")
            if marker_set.hasKey("bar")
            else marker_set.get("barbell_shaft")
        )
        assert bar_marker is not None, f"{exercise} should have bar marker"
