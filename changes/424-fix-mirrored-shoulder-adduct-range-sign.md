---
issue: 424
summary: "Fix mirrored shoulder-adduct range sign/direction; discover and work around the wrist's own range binding the snatch grip width"
dl_state: "in_review"
next_step: "Review and merge; #426 tracks the remaining grip-width gap."
title: "Fix Mirrored Shoulder Adduction/Abduction Range Sign Convention"
owner: "claude"
branch: "claude/shoulder-rom-424"
paths: "src/opensim_models/shared/body/body_model.py,src/opensim_models/shared/body/arm_geometry.py,src/opensim_models/exercises/snatch/snatch_model.py,src/opensim_models/shared/parity/parity_divergences.json,tests/unit/shared/test_body_model.py,tests/unit/shared/test_arm_geometry.py,tests/parity/test_barbell_grip_residual.py"
---

Confirmed empirically with real-OpenSim forward kinematics (perturbing shoulder_l_adduct/shoulder_r_adduct and hip_l_adduct/hip_r_adduct +-0.2 rad from the neutral squat pose and reading hand_l/hand_r and foot_l/foot_r ground-frame position) that positive adduct = adduction toward the midline, negative = abduction, for both joints. Hip's declared range (-45 deg abduction / +30 deg adduction) was already anatomically correct; only the shoulder's range had the sign/magnitude backwards (-30 deg abduction / +180 deg adduction). Swapped to -180 deg / +30 deg (Kapandji 2008), matching Pinocchio_Models#461 and MuJoCo_Models#441's convention.

Discovered while fixing this that OpenSim's barbell-to-hand attachment rigidly ties both hands' orientation to the single shaft (a zero-DOF WeldJoint on the left, a WeldConstraint on the right), so the wrist's counter-rotation that keeps the bar level must *exactly* cancel the shoulder's tilt -- not approximately, and not independently clampable to the wrist's own range, or OpenSim's initSystem() silently redistributes the mismatch across both wrists at assembly time (confirmed empirically: clamping produced ~15.17 deg of drift on each wrist). `shoulder_adduct_for_grip` now clamps its angle to the intersection of the shoulder's own range and the range the wrist's exact counter-rotation can reach, so this can never happen. This means the snatch's achievable grip width is still ~0.4585 m (not the documented 0.58 m) -- the real bottleneck was always the wrist's own range, which the old, mislabeled shoulder range happened to numerically match by coincidence. Filed and updated OpenSim_Models#426 to track closing that real, remaining gap; #424 is not closed by this PR.
