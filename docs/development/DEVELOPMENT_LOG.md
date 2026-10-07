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
