# Development Log — OpenSim_Models

State table for every feature in flight in this repository. Update
entries **in place**; never append dated sections. One entry per
feature, from proposal to ship. See the `development-logs` section of
`AGENTS.md` for the binding rules and
`shared_scripts/development_log.py` for the validator.

- **Portfolio:** work
- **WIP limit:** 5
- **Last audited:** 2026-08-28 by bootstrap

## States

`proposed` → `in_progress` → `in_review` → `shipped`, with `parked`
reachable from any live state and `abandoned` from `parked`.
`shipped` never returns to `in_progress`; open a new entry instead.

## Active

### DL-#397 · Drop Python 3.10 From CI Matrix and Pyproject.Toml

- **State:** in_review
- **Owner:** unassigned
- **Issue:** #397
- **Branch:** fix/397-drop-py310
- **PR:** #460
- **Paths:** see #460
- **Started:** 2026-10-14
- **Last verified:** 2026-10-14 (`3e7063c8`; collated from changes/397-drop-python-3-10-from-ci-matrix-and-pypr.md)
- **Summary:** Drop Python 3.10 from CI matrix and pyproject.toml
- **Next step:** Merge the PR.

### DL-#391 · Export Per-Foot and Total GRF With CoP From SmoothSphereHalfSpaceForce, With a Real-OpenSim Standing Test

- **State:** in_review
- **Owner:** unassigned
- **Issue:** #391
- **Branch:** feat/391-grf-cop
- **PR:** #452
- **Paths:** see #452
- **Started:** 2026-10-13
- **Last verified:** 2026-10-13 (`42393b8a`; collated from changes/391-export-per-foot-and-total-grf-with-cop-f.md)
- **Summary:** Export per-foot and total GRF with CoP from SmoothSphereHalfSpaceForce, with a real-OpenSim standing test
- **Next step:** Merge the PR after CI's real-OpenSim lane passes.

### DL-#386 · Bring Src Files Under the 300-Line Budget and Enforce It in CI

- **State:** in_review
- **Owner:** unassigned
- **Issue:** #386
- **Branch:** fix/386-300-line-budget
- **PR:** #445
- **Paths:** see #445
- **Started:** 2026-10-13
- **Last verified:** 2026-10-13 (`f847d1df`; collated from changes/386-bring-src-files-under-the-300-line-budge.md)
- **Summary:** Bring src files under the 300-line budget and enforce it in CI
- **Next step:** Merge the PR.

### DL-#393 · \ Derive Joint Limits From the Bundle,Not Rounded-Radian Literals\

- **State:** in_review
- **Owner:** unassigned
- **Issue:** #393
- **Branch:** feat/393-derive-joint-limits
- **PR:** #446
- **Paths:** see #446
- **Started:** 2026-10-13
- **Last verified:** 2026-10-13 (`981a6435`; collated from changes/393-derive-joint-limits-from-the-bundle-not.md)
- **Summary:** \ Derive joint limits from the bundle,not rounded-radian literals\
- **Next step:** \Merge the PR.\

### DL-#434 · \ Name Gait and Sit-to-Stand Phases per Standard V2.0\

- **State:** in_review
- **Owner:** unassigned
- **Issue:** #434
- **Branch:** fix/434-gait-sts-phases
- **PR:** #440
- **Paths:** see #440
- **Started:** 2026-10-12
- **Last verified:** 2026-10-12 (`d9ef8ec3`; collated from changes/434-name-gait-and-sit-to-stand-phases-per-st.md)
- **Summary:** \ Name Gait and Sit-to-Stand Phases per Standard v2.0\
- **Next step:** \Merge the PR.\

### DL-#384 · Every Barbell Lift's Generated Model Starts at the Standard V2.1 Start Via-Pose (Coordinates, Pelvis Root, Bar, Palm Grip, Feet) With the Spec Load; Bench Start Contact Force Fixed (LIFT-3, UpstreamDrift#11743)

- **State:** in_review
- **Owner:** unassigned
- **Issue:** #384
- **Branch:** claude/lift-3-spec-start-poses
- **PR:** #437
- **Paths:** see #437
- **Started:** 2026-10-12
- **Last verified:** 2026-10-12 (`cddbdecd`; collated from changes/384-every-barbell-lift-s-generated-model-sta.md)
- **Summary:** Every barbell lift's generated model starts at the standard v2.1 start via-pose (coordinates, pelvis root, bar, palm grip, feet) with the spec load; bench start contact force fixed (LIFT-3, UpstreamDrift#11743)
- **Next step:** Merge the PR; settled static GRF check and #434 gait/sit-to-stand phases remain.

### DL-#426 · Keep Bar Level via Weld Frame Orientation in the Tilted Hand Frame

- **State:** in_review
- **Owner:** claude
- **Issue:** #426
- **Branch:** claude/grip-weld-orientation-426
- **PR:** #429
- **Paths:** src/opensim_models/exercises/base.py,src/opensim_models/exercises/clean_and_jerk/clean_and_jerk_model.py,src/opensim_models/exercises/deadlift/deadlift_model.py,src/opensim_models/exercises/snatch/snatch_model.py,src/opensim_models/shared/body/arm_geometry.py,src/opensim_models/shared/body/body_model.py,src/opensim_models/shared/utils/constraint_helpers.py,src/opensim_models/shared/utils/xml_helpers/\_joints.py,tests/parity/test_barbell_grip_residual.py,tests/unit/shared/test_arm_geometry.py,tests/unit/shared/test_xml_helpers.py,tests/unit/exercises/test_base.py,tests/unit/shared/test_constraint_helpers.py
- **Started:** 2026-10-10
- **Last verified:** 2026-10-10 (`5430b753`; collated from changes/426-reach-the-snatch-s-documented-0-58-m-gri.md)
- **Summary:** Reach the snatch's documented 0.58 m grip by keeping hand orientation consistent with the shaft via the grip weld's own frame instead of a wrist counter-rotation
- **Next step:** Review and merge

### DL-#424 · Fix Mirrored Shoulder Adduction/Abduction Range Sign Convention

- **State:** in_review
- **Owner:** claude
- **Issue:** #424
- **Branch:** claude/shoulder-rom-424
- **PR:** #427
- **Paths:** src/opensim_models/shared/body/body_model.py,src/opensim_models/shared/body/arm_geometry.py,src/opensim_models/exercises/snatch/snatch_model.py,src/opensim_models/shared/parity/parity_divergences.json,tests/unit/shared/test_body_model.py,tests/unit/shared/test_arm_geometry.py,tests/parity/test_barbell_grip_residual.py
- **Started:** 2026-10-10
- **Last verified:** 2026-10-10 (`d9992adb`; collated from changes/424-fix-mirrored-shoulder-adduct-range-sign.md)
- **Summary:** Fix mirrored shoulder-adduct range sign/direction; discover and work around the wrist's own range binding the snatch grip width
- **Next step:** Review and merge; #426 tracks the remaining grip-width gap.

### DL-#394 · Symmetric Barbell Grip at the Neutral Pose

- **State:** in_review
- **Owner:** claude
- **Issue:** #394
- **Branch:** claude/grip-residuals-394
- **PR:** #423
- **Paths:** src/opensim_models/shared/body/arm_geometry.py,src/opensim_models/shared/body/body_model.py,src/opensim_models/exercises/deadlift/deadlift_model.py,src/opensim_models/exercises/clean_and_jerk/clean_and_jerk_model.py,src/opensim_models/exercises/snatch/snatch_model.py,src/opensim_models/exercises/bench_press/bench_press_model.py,tests/parity/test_barbell_grip_residual.py
- **Started:** 2026-10-10
- **Last verified:** 2026-10-10 (`085ce939`; collated from changes/394-derive-shoulder-adduction-from-the-reque.md)
- **Summary:** Derive shoulder adduction from the requested grip width (shared/body/arm_geometry.py) so both hand-to-bar attachments agree at the neutral pose for deadlift, clean_and_jerk, snatch and bench_press; snatch grip is narrowed to the widest width the shoulder ROM can reach.
- **Next step:** Open the PR and get it reviewed/merged.

### DL-#389 · Add an InverseDynamicsTool Wrapper With a Real-OpenSim Test

- **State:** in_review
- **Owner:** unassigned
- **Issue:** #389
- **Branch:** fix/389-inverse-dynamics-tool
- **PR:** #417
- **Paths:** see #417
- **Started:** 2026-10-09
- **Last verified:** 2026-10-09 (`74afedc4`; collated from changes/389-add-an-inversedynamicstool-wrapper-with.md)
- **Summary:** Add an InverseDynamicsTool wrapper with a real-OpenSim test
- **Next step:** Review and merge PR.

### DL-#383 · Anatomical Joint Axes: X Forward, Z Lateral, Mirrored Left Side

- **State:** in_review
- **Owner:** unassigned
- **Issue:** #383
- **Branch:** fix/issue-383-hip-flexion-axis
- **PR:** #401
- **Paths:** see #401
- **Started:** 2026-10-05
- **Last verified:** 2026-10-05 (`adeacfc0`; collated from changes/383-hip-flexion-axis.md)
- **Summary:** OpenSim body model now uses one axis convention: X forward, Z lateral with left at -Z (canonical +Y). Hip/shoulder/lumbar/neck become explicit-axis CustomJoints (flexion anterior-positive; adduction, internal rotation, inversion and wrist deviation mirrored left/right); barbell lies along Z; seated sit_to_stand lifts the knees so the feet rest on the floor.
- **Next step:** Repository_Management#2011 should adopt (or amend) these positive senses in the standard v2 kinematics block; MuJoCo#410 and Drake#373 need the same flexion-axis fix.

### DL-#1606 · Adopt Mermaid C4 Architecture Map Contract

- **Issue:** #1606 (https://github.com/D-sorganization/Repository_Management/issues/1606)
- **State:** in_progress
- **Owner:** local (agent session bd082424-e57d-40ba-9962-3bf4420a5b33)
- **Branch:** docs/1606-c4-architecture-map
- **PR:** not created
- **Paths:** docs/architecture/C4.md, scripts/architecture_map_contract.py, tests/scripts/test_architecture_map_contract.py, .github/workflows/architecture-map-contract.yml
- **Started:** 2026-09-10
- **Last verified:** 2026-09-10 (`407ada1`)
- **Next step:** Open PR and merge with passing architecture map contract workflow.
- **Summary:** Establish and enforce the maintainable Mermaid C4 architecture-map contract for OpenSim_Models per Repository_Management Epic #1594.

## Shipped (Last 90 Days)

### DL-#390 · Integrate a Manager Forward Simulation With CoordinateActuators (#390)

- **State:** shipped
- **Owner:** unassigned
- **Issue:** #390
- **Branch:** merged via #454
- **PR:** #454
- **Paths:** see #454
- **Started:** 2026-10-13
- **Last verified:** 2026-10-13 (`0340d65e`; collated from changes/390-forward-simulation-manager.md)
- **Summary:** Integrate a Manager forward simulation with CoordinateActuators (#390)
- **Next step:** Shipped in PR #454.

### DL-#388 · Add InverseKinematicsTool Wrapper With Real-OpenSim Test (#388)

- **State:** shipped
- **Owner:** unassigned
- **Issue:** #388
- **Branch:** merged via #454
- **PR:** #454, #453
- **Paths:** see #454
- **Started:** 2026-10-13
- **Last verified:** 2026-10-14 (`2675a351`; collated from changes/388-inverse-kinematics-tool-wrapper.md)
- **Summary:** Add InverseKinematicsTool wrapper with real-OpenSim test (#388)
- **Next step:** Shipped in PR #454.

### DL-#380 · Re-Sync Vendored Model-Parity Bundle to Repository_Management Main (Standard V2.1, assemble.py Phase_Names From RM#2089)

- **State:** shipped
- **Owner:** unassigned
- **Issue:** #380
- **Branch:** merged via #456
- **PR:** #456
- **Paths:** see #456
- **Started:** 2026-10-13
- **Last verified:** 2026-10-13 (`4d82e996`; collated from changes/380-parity-bundle-resync.md)
- **Summary:** Re-sync vendored model-parity bundle to Repository_Management main (standard v2.1, assemble.py phase_names from RM#2089)
- **Next step:** Shipped in PR #456.

### DL-#387 · Add MarkerSet With Standard Human and Equipment Markers (#387)

- **State:** shipped
- **Owner:** unassigned
- **Issue:** #387
- **Branch:** merged via #451
- **PR:** #451, #454, #453
- **Paths:** see #451
- **Started:** 2026-10-13
- **Last verified:** 2026-10-14 (`2675a351`; collated from changes/387-add-markerset-with-standard-human-and-eq.md)
- **Summary:** Add MarkerSet with standard human and equipment markers (#387)
- **Next step:** Shipped in PR #451.

### DL-#416 · Add Tests Measuring Floor-Pull Bar Height Above the Lowest Sole (#416)

- **State:** shipped
- **Owner:** unassigned
- **Issue:** #416
- **Branch:** merged via #447
- **PR:** #447
- **Paths:** see #447
- **Started:** 2026-10-13
- **Last verified:** 2026-10-13 (`e9ff9511`; collated from changes/416-add-tests-measuring-floor-pull-bar-heigh.md)
- **Summary:** Add tests measuring floor-pull bar height above the lowest sole (#416)
- **Next step:** Shipped in PR #447.

### DL-#396 · Rename Wrist Deviation and Ankle Inversion Coordinates to Deviate and Invert per Standard V2.0

- **State:** shipped
- **Owner:** unassigned
- **Issue:** #396
- **Branch:** merged via #443
- **PR:** #443
- **Paths:** see #443
- **Started:** 2026-10-13
- **Last verified:** 2026-10-13 (`77942b8e`; collated from changes/396-rename-wrist-deviation-and-ankle-inversi.md)
- **Summary:** Rename wrist deviation and ankle inversion coordinates to deviate and invert per standard v2.0
- **Next step:** Shipped in PR #443.

### DL-#414 · Lift Objectives Consume the Standard V2.0 Exercise Spec (Phase Names, Timing, Start/Catch/Lockout Via-Poses) With Targets Keyed by Model Coordinate Names; Bench_Press Weld Root Now Conforms (LIFT-2, UpstreamDrift#11742)

- **State:** shipped
- **Owner:** unassigned
- **Issue:** #414
- **Branch:** claude/lift-2-standard-v2
- **PR:** #435, #442
- **Paths:** see #435
- **Started:** 2026-10-12
- **Last verified:** 2026-10-13 (`b904780d`; collated from changes/414-map-gait-and-sit-to-stand-phase-targets.md)
- **Summary:** Lift objectives consume the standard v2.0 exercise spec (phase names, timing, start/catch/lockout via-poses) with targets keyed by model coordinate names; bench_press weld root now conforms (LIFT-2, UpstreamDrift#11742)
- **Next step:** Shipped in PR #435.

### DL-#1917 · Sync the Agent-Identity Managed Block: The Owner's Personal Token Is an Approved Agent Identity

- **State:** shipped
- **Owner:** unassigned
- **Issue:** #1917
- **Branch:** merged via #431
- **PR:** #431
- **Paths:** see #431
- **Started:** 2026-10-11
- **Last verified:** 2026-10-11 (`d656dee9`; collated from changes/1917-sync-the-agent-identity-managed-block-th.md)
- **Summary:** Sync the agent-identity managed block: the owner's personal token is an approved agent identity
- **Next step:** Shipped in PR #431.

### DL-#392 · Derive Segment Radius and Inertia From Standard Radius_Frac Instead of Uniform Density

- **State:** shipped
- **Owner:** unassigned
- **Issue:** #392
- **Branch:** merged via #421
- **PR:** #421
- **Paths:** see #421
- **Started:** 2026-10-10
- **Last verified:** 2026-10-10 (`185e59e2`; collated from changes/392-derive-segment-radius-and-inertia-from-s.md)
- **Summary:** Derive segment radius and inertia from standard radius_frac instead of uniform density
- **Next step:** Shipped in PR #421.

### DL-#398 · Remove Stray Fix.Diff From Repo Root

- **State:** shipped
- **Owner:** unassigned
- **Issue:** #398
- **Branch:** merged via #419
- **PR:** #419
- **Paths:** see #419
- **Started:** 2026-10-10
- **Last verified:** 2026-10-10 (`96671dc5`; collated from changes/398-remove-stray-fix-diff-from-repo-root.md)
- **Summary:** Remove stray fix.diff from repo root
- **Next step:** Shipped in PR #419.

### DL-#2011 · Fingerprint Reports Test-Pose Origins in the Pelvis Frame

- **State:** shipped
- **Owner:** unassigned
- **Issue:** #2011
- **Branch:** feat/issue-2011-test-pose-origins
- **PR:** #406
- **Paths:** see #406
- **Started:** 2026-10-07
- **Last verified:** 2026-10-07 (`a0590334`; collated from changes/2011-test-pose-origins.md)
- **Summary:** Re-vendored parity bundle (standard 1.2.0, topology.py, Repository_Management#2011 slice 2). The OpenSim fingerprint reports the pelvis rotation and segment origins at the standard's three test poses; conformance checks them against the reference forward kinematics with zero origin and pose divergences for every exercise.
- **Next step:** Shipped in PR #406.

### DL-#410 · CI: Isolate RUSTUP_HOME/CARGO_HOME per Workspace in Rust Gate (RM#2021)

- **State:** shipped
- **Owner:** unassigned
- **Issue:** #410
- **Branch:** merged via #411
- **PR:** #411
- **Paths:** see #411
- **Started:** 2026-10-07
- **Last verified:** 2026-10-07 (`251b7723`; collated from changes/410-ci-isolate-rustup-home-cargo-home-per-wo.md)
- **Summary:** CI: isolate RUSTUP_HOME/CARGO_HOME per workspace in Rust Gate (RM#2021)
- **Next step:** Shipped in PR #411.

### DL-#407 · SECURITY: Guard Fork PRs Off the Self-Hosted Fleet; Vendor Fork_Pr_Runner_Guard Checker, Fork-Route/Guard 9 Fleet-Capable Jobs, Add CI Check (RM#1989)

- **State:** shipped
- **Owner:** unassigned
- **Issue:** #407
- **Branch:** merged via #408
- **PR:** #408
- **Paths:** see #408
- **Started:** 2026-10-07
- **Last verified:** 2026-10-07 (`6c1fc53e`; collated from changes/407-security-guard-fork-prs-off-the-self-hos.md)
- **Summary:** SECURITY: guard fork PRs off the self-hosted fleet; vendor fork_pr_runner_guard checker, fork-route/guard 9 fleet-capable jobs, add CI check (RM#1989)
- **Next step:** Shipped in PR #408.

### DL-#395 · Fingerprint Reports Measured Coordinate Axes

- **State:** shipped
- **Owner:** unassigned
- **Issue:** #395
- **Branch:** feat/issue-395-coordinate-axes
- **PR:** #404
- **Paths:** see #404
- **Started:** 2026-10-06
- **Last verified:** 2026-10-06 (`93b9e89a`; collated from changes/395-coordinate-axes.md)
- **Summary:** Re-vendored parity bundle (standard 1.1.0, kinematics.py). The OpenSim fingerprint now measures every coordinate's rotation axis in the real engine; conformance checks axes and lateral sides with zero divergences for all seven exercises.
- **Next step:** Shipped in PR #404.

### DL-#2019 · Vendor RM-5 Change-Fragment Tooling and Test Suite

- **State:** shipped
- **Owner:** unassigned
- **Issue:** #2019
- **Branch:** feat/2019-vendor-rm-5-change-fragment-tooling
- **PR:** #399, #400
- **Paths:** see #399
- **Started:** 2026-10-05
- **Last verified:** 2026-10-05 (`d5097937`; collated from changes/2019-wire-collate-changes-workflow-and-check.md)
- **Summary:** vendor RM-5 change-fragment tooling and test suite
- **Next step:** Shipped in PR #399.

Entries stay here for 90 days after merge, then move to the archive.

## Archive

Older entries live in `DEVELOPMENT_LOG_ARCHIVE_<year>.md`.
