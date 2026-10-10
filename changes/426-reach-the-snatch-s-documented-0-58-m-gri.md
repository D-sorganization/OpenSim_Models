---
issue: 426
summary: "Reach the snatch's documented 0.58 m grip by keeping hand orientation consistent with the shaft via the grip weld's own frame instead of a wrist counter-rotation"
dl_state: "in_review"
next_step: "Review and merge"
title: "Keep Bar Level via Weld Frame Orientation in the Tilted Hand Frame"
owner: "claude"
branch: "claude/grip-weld-orientation-426"
paths: "src/opensim_models/exercises/base.py,src/opensim_models/exercises/clean_and_jerk/clean_and_jerk_model.py,src/opensim_models/exercises/deadlift/deadlift_model.py,src/opensim_models/exercises/snatch/snatch_model.py,src/opensim_models/shared/body/arm_geometry.py,src/opensim_models/shared/body/body_model.py,src/opensim_models/shared/utils/constraint_helpers.py,src/opensim_models/shared/utils/xml_helpers/_joints.py,tests/parity/test_barbell_grip_residual.py,tests/unit/shared/test_arm_geometry.py,tests/unit/shared/test_xml_helpers.py,tests/unit/exercises/test_base.py,tests/unit/shared/test_constraint_helpers.py"
---

#424 found the real bottleneck for the snatch's documented 0.58 m grip was the wrist's own range of motion, not the shoulder's: the wrist's exact counter-rotation (`wrist_deviation = -shoulder_adduct`) that kept the hand's orientation consistent with the rigidly-welded shaft (a zero-DOF `WeldJoint` on the left hand, a `WeldConstraint` on the right) could not cancel the ~45.16 deg of shoulder abduction the full grip needs without exceeding its own +30 deg bound, clamping the achieved width to ~0.4585 m.

This PR removes the wrist-counter-rotation mechanism entirely for deadlift, clean_and_jerk and snatch (the three exercises built on `attach_barbell_to_hands`). Instead, the grip weld's own frame carries the exact inverse of each hand's tilt: confirmed with real-OpenSim forward kinematics (perturbing `shoulder_l_adduct`/`shoulder_r_adduct` from an otherwise-zeroed pose on a barbell-free exercise, to isolate the effect), `hand_l = RotX(-shoulder_l_adduct)` and `hand_r = RotX(+shoulder_r_adduct)` about the shared mirrored adduct/deviation axis. `attach_barbell_to_hands` gained a `hand_tilt` parameter (the common `shoulder_{l,r}_adduct` value, defaulting to 0): the left `WeldJoint`'s parent (hand_l) offset frame gets `orientation_in_parent = (hand_tilt, 0, 0)`, and the right `WeldConstraint`'s frame on hand_r gets `orientation_in_body_1 = (-hand_tilt, 0, 0)`. With wrist deviation at 0, this exactly cancels each hand's local tilt (`RotX(-hand_tilt) * RotX(hand_tilt) = I`), so the shaft ends up exactly as level as it was under the old exact-cancellation mechanism, now bounded only by the shoulder's own (much larger) range of motion. `shoulder_adduct_for_grip` no longer clamps against `WRIST_DEVIATION_RANGE`.

Bench press is explicitly out of scope and untouched: it keeps its existing wrist-cancellation mechanism byte-identical (`wrist_{l,r}_deviation = -shoulder_adduct`, nonzero), since its narrower grip never needed the wrist's range extended in the first place.

Real-OpenSim measurements at the neutral pose (position residual, orientation residual, coordinate drift all ~0 for every exercise):

| exercise | shoulder_adduct | wrist_deviation | achieved grip | pos residual L/R | orient residual L/R |
| --- | --- | --- | --- | --- | --- |
| deadlift | -23.5351 deg | 0 deg | 0.4000 m | 0.0/0.0 mm | 0.0/0.0 deg |
| clean_and_jerk | -8.1136 deg | 0 deg | 0.2500 m | 0.0/0.0 mm | 0.0/0.0 deg |
| snatch | -45.1635 deg | 0 deg | **0.5800 m** | 0.0/0.0 mm | 0.0/0.0 deg |
| bench_press (unchanged) | -23.5351 deg | +23.5351 deg | 0.4000 m | 0.0/0.0 mm | 0.0/0.0 deg |

`tests/parity/test_barbell_grip_residual.py` stays green throughout (TDD: new orientation-residual, wrist-zero, mirror-symmetry and bench-unchanged tests written first, confirmed red, then green); no tolerance loosened, no wrist range widened, no residual reintroduced.
