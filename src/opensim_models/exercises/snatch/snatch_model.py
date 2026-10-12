"""Snatch model builder.

The snatch is a single continuous motion that lifts the barbell from the
floor to overhead in one movement. The lifter uses a wide (snatch) grip,
pulls the bar explosively, then drops under it into an overhead squat.

Phases:
1. First pull — bar leaves the floor (deadlift-like, wide grip)
2. Transition / scoop — knees re-bend, torso becomes more vertical
3. Second pull — explosive triple extension (ankle, knee, hip)
4. Turnover — lifter pulls under the bar, rotating arms overhead
5. Catch — overhead squat position (deep squat, arms locked overhead)
6. Recovery — stand up from overhead squat to full extension

Biomechanical notes:
- Grip width: the standard's snatch grip (``grip.width_m``), the widest of
  the barbell lifts; the shoulder abduction it needs comes from the spec
  ``start`` via-pose, within the shoulder's corrected range (#424)
- Primary movers: entire posterior chain, deltoids, trapezius
- Requires extreme shoulder mobility for overhead position
- Bar path is close to the body (S-curve trajectory)

The barbell is welded to both palm centres. The default state is the
standard's snatch ``start`` via-pose (UpstreamDrift#11743).
"""

from __future__ import annotations

import logging

from opensim_models.exercises.spec_start import SpecLiftModelBuilder, spec_lift_config

logger = logging.getLogger(__name__)


class SnatchModelBuilder(SpecLiftModelBuilder):
    """Builds a snatch OpenSim model with wide grip."""

    @property
    def exercise_name(self) -> str:
        return "snatch"

    @property
    def spec_exercise(self) -> str:
        return "snatch"


def build_snatch_model(
    body_mass: float = 80.0,
    height: float = 1.75,
    plate_mass_per_side: float | None = None,
) -> str:
    """Convenience function to build a snatch model XML string.

    ``plate_mass_per_side=None`` is the spec load.
    """
    config = spec_lift_config("snatch", body_mass, height, plate_mass_per_side)
    return SnatchModelBuilder(config).build()
