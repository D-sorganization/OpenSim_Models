---
issue: 383
summary: "OpenSim body model now uses one axis convention: X forward, Z lateral with left at -Z (canonical +Y). Hip/shoulder/lumbar/neck become explicit-axis CustomJoints (flexion anterior-positive; adduction, internal rotation, inversion and wrist deviation mirrored left/right); barbell lies along Z; seated sit_to_stand lifts the knees so the feet rest on the floor."
dl_state: "in_review"
next_step: "Repository_Management#2011 should adopt (or amend) these positive senses in the standard v2 kinematics block; MuJoCo#410 and Drake#373 need the same flexion-axis fix."
title: "Anatomical Joint Axes: X Forward, Z Lateral, Mirrored Left Side"
branch: "fix/issue-383-hip-flexion-axis"
---
