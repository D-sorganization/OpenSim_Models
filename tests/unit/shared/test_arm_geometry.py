"""Tests for shoulder-abduction grip geometry (#394, #424)."""

from __future__ import annotations

import math

import pytest

from opensim_models.exercises.constants import _SNATCH_GRIP_HALF_WIDTH
from opensim_models.shared.body import BodyModelSpec
from opensim_models.shared.body.arm_geometry import (
    shoulder_adduct_for_grip,
    wrist_deviation_for_shoulder_adduct,
)
from opensim_models.shared.body.body_model import WRIST_DEVIATION_RANGE


class TestSnatchGripReachesRequestedWidth:
    """Issue #424: the snatch's wide grip was clamped to ~0.46 m by the
    shoulder's previously mirrored adduction range. With the anatomical
    range, the shoulder's own range of motion no longer binds, and the
    full requested grip width is reachable."""

    def test_snatch_grip_reaches_requested_width(self) -> None:
        spec = BodyModelSpec()
        _, feasible = shoulder_adduct_for_grip(spec, _SNATCH_GRIP_HALF_WIDTH)
        assert feasible == pytest.approx(_SNATCH_GRIP_HALF_WIDTH, abs=1e-3)


class TestWristDeviationForShoulderAdduct:
    """The wrist counter-rotation that keeps the hand level must itself stay
    within the wrist's own declared range of motion (#424)."""

    def test_cancels_small_adduct_exactly(self) -> None:
        shoulder_adduct = math.radians(-20)
        result = wrist_deviation_for_shoulder_adduct(shoulder_adduct)
        assert result == pytest.approx(math.radians(20))

    def test_clamps_when_cancellation_exceeds_wrist_range(self) -> None:
        """The snatch's full grip needs ~45.16 deg of shoulder abduction
        (#424); cancelling it exactly would need +45.16 deg of wrist
        deviation, past the wrist's own +30 deg bound."""
        shoulder_adduct = math.radians(-45.164)
        _, hi = WRIST_DEVIATION_RANGE
        result = wrist_deviation_for_shoulder_adduct(shoulder_adduct)
        assert result == pytest.approx(hi)

    def test_result_always_within_wrist_range(self) -> None:
        lo, hi = WRIST_DEVIATION_RANGE
        for degrees in (-180, -90, -45.164, -20, 0, 20, 30):
            result = wrist_deviation_for_shoulder_adduct(math.radians(degrees))
            assert lo - 1e-9 <= result <= hi + 1e-9

    def test_rejects_non_finite(self) -> None:
        with pytest.raises(ValueError, match="finite"):
            wrist_deviation_for_shoulder_adduct(float("nan"))
