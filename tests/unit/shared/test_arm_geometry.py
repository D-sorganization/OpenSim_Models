"""Tests for shoulder-abduction grip geometry (#394, #424, #426)."""

from __future__ import annotations

import math

import pytest

from opensim_models.exercises.constants import (
    _CLEAN_GRIP_HALF_WIDTH,
    _SNATCH_GRIP_HALF_WIDTH,
)
from opensim_models.shared.body import BodyModelSpec
from opensim_models.shared.body.arm_geometry import shoulder_adduct_for_grip
from opensim_models.shared.body.body_model import SHOULDER_ADDUCT_RANGE


class TestShoulderAdductForGripRespectsOnlyTheShouldersOwnRange:
    """``shoulder_adduct_for_grip`` clamps its angle to the shoulder's own
    declared range of motion only (#426).

    #424 additionally clamped to the range the wrist's exact counter-
    rotation (``-shoulder_adduct``) could cancel without exceeding its own
    declared range, because the wrist coordinate used to be the mechanism
    that kept the hand's orientation consistent with the rigidly-welded
    shaft. #426 replaces that wrist counter-rotation with an orientation
    offset baked into the grip weld's own frame (see
    ``exercises.base.attach_barbell_to_hands``), so the wrist no longer
    needs to move at all and this function no longer needs to protect it.
    """

    def test_wide_grip_now_reaches_the_full_requested_width(self) -> None:
        """The snatch's 0.58 m grip needs ~45.16 deg of shoulder abduction,
        comfortably within the shoulder's own (much larger) range, so it is
        no longer clamped at all -- unlike before #426, when the wrist's
        own +30 deg bound (not the shoulder's) capped it at ~0.4585 m."""
        spec = BodyModelSpec()
        theta, feasible = shoulder_adduct_for_grip(spec, _SNATCH_GRIP_HALF_WIDTH)
        assert feasible == pytest.approx(_SNATCH_GRIP_HALF_WIDTH, abs=1e-6)
        assert theta == pytest.approx(math.radians(-45.16), abs=1e-3)

    def test_narrow_grip_is_unaffected(self) -> None:
        """Clean/deadlift/bench's narrower grips need much less abduction
        than the shoulder allows, so they reach their full requested width
        exactly, as before."""
        spec = BodyModelSpec()
        _, feasible = shoulder_adduct_for_grip(spec, _CLEAN_GRIP_HALF_WIDTH)
        assert feasible == pytest.approx(_CLEAN_GRIP_HALF_WIDTH, abs=1e-6)

    def test_extreme_grip_is_still_clamped_by_the_shoulders_own_range(self) -> None:
        """A grip offset narrower than the torso midline demands adduction
        past the shoulder's own declared limit, so the shoulder's own range
        (not the wrist's) is still the backstop."""
        spec = BodyModelSpec()
        _, hi = SHOULDER_ADDUCT_RANGE
        theta, feasible = shoulder_adduct_for_grip(spec, -1.0)
        assert theta == pytest.approx(hi)
        assert feasible > -1.0  # clamped short of the requested -1.0 m

    def test_rejects_non_finite_grip_offset(self) -> None:
        spec = BodyModelSpec()
        with pytest.raises(ValueError, match="finite"):
            shoulder_adduct_for_grip(spec, float("nan"))
