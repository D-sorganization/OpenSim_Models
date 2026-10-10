---
issue: 394
summary: "Derive shoulder adduction from the requested grip width (shared/body/arm_geometry.py) so both hand-to-bar attachments agree at the neutral pose for deadlift, clean_and_jerk, snatch and bench_press; snatch grip is narrowed to the widest width the shoulder ROM can reach."
dl_state: "in_review"
next_step: "Open the PR and get it reviewed/merged."
title: "Symmetric Barbell Grip at the Neutral Pose"
owner: "claude"
branch: "claude/grip-residuals-394"
paths: "src/opensim_models/shared/body/arm_geometry.py,src/opensim_models/shared/body/body_model.py,src/opensim_models/exercises/deadlift/deadlift_model.py,src/opensim_models/exercises/clean_and_jerk/clean_and_jerk_model.py,src/opensim_models/exercises/snatch/snatch_model.py,src/opensim_models/exercises/bench_press/bench_press_model.py,tests/parity/test_barbell_grip_residual.py"
---
