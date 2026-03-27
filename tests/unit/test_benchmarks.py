"""Performance benchmark tests for model generation.

These tests verify that model generation completes within reasonable
time bounds. They are marked with @pytest.mark.slow so they can be
skipped in fast CI runs.
"""

from __future__ import annotations

import time

import pytest

from opensim_models.exercises.bench_press.bench_press_model import (
    build_bench_press_model,
)
from opensim_models.exercises.clean_and_jerk.clean_and_jerk_model import (
    build_clean_and_jerk_model,
)
from opensim_models.exercises.deadlift.deadlift_model import build_deadlift_model
from opensim_models.exercises.snatch.snatch_model import build_snatch_model
from opensim_models.exercises.squat.squat_model import build_squat_model

_BUILDERS = {
    "squat": build_squat_model,
    "bench_press": build_bench_press_model,
    "deadlift": build_deadlift_model,
    "snatch": build_snatch_model,
    "clean_and_jerk": build_clean_and_jerk_model,
}

# Maximum allowed time per model generation (seconds)
_MAX_GENERATION_TIME = 2.0


class TestModelGenerationPerformance:
    """Verify model generation completes quickly."""

    @pytest.mark.parametrize("name,builder", list(_BUILDERS.items()))
    def test_single_model_under_time_limit(self, name, builder):
        start = time.perf_counter()
        xml_str = builder()
        elapsed = time.perf_counter() - start
        assert (
            elapsed < _MAX_GENERATION_TIME
        ), f"{name} took {elapsed:.3f}s (limit: {_MAX_GENERATION_TIME}s)"
        assert len(xml_str) > 0

    def test_all_models_batch_under_time_limit(self):
        """Generating all five models should complete in under 10 seconds."""
        start = time.perf_counter()
        for builder in _BUILDERS.values():
            builder()
        elapsed = time.perf_counter() - start
        assert elapsed < 10.0, f"Batch generation took {elapsed:.3f}s (limit: 10s)"

    @pytest.mark.parametrize("name,builder", list(_BUILDERS.items()))
    def test_xml_output_reasonable_size(self, name, builder):
        """Generated XML should be between 1 KB and 1 MB."""
        xml_str = builder()
        size = len(xml_str.encode("utf-8"))
        assert 1_000 < size < 1_000_000, f"{name} XML is {size} bytes (expected 1KB-1MB)"
