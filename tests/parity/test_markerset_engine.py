# SPDX-License-Identifier: MIT
"""Real-engine OpenSim test for MarkerSet (#387)."""

from __future__ import annotations

from pathlib import Path

import pytest

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.model_pack import list_exercises

pytestmark = pytest.mark.requires_opensim

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
        marker_names = {
            marker_set.get(i).getName() for i in range(marker_set.getSize())
        }
        bar_name = "bar" if "bar" in marker_names else "barbell_shaft"
        assert bar_name in marker_names, f"{exercise} should have bar marker"
        assert marker_set.get(bar_name) is not None
