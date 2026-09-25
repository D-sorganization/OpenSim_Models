# Project Charter

> Drafted 2026-09-25 by the fleet charter sweep (Gemini) from README, git history, and open issues/PRs.
> The project-steward role keeps this current; owners should correct feature statuses.

## End Goal

OpenSim_Models provides a lightweight, contract-driven Python library and CLI (`opensim-models`) for generating valid OpenSim `.osim` musculoskeletal XML models for classical barbell exercises (back squat, bench press, deadlift, snatch, clean and jerk) and baseline functional movements (gait, sit-to-stand). Done means all supported exercise builders reliably assemble anthropometrically scaled, kinematically sound OpenSim XML documents with rigorous Design-by-Contract input/output validation, without requiring a live OpenSim runtime, while exposing a standardized `model_pack/v1` entrypoint for automated discovery by UpstreamDrift and fleet biomechanical tooling.

## Non-Goals

- Live OpenSim dynamic simulation runtime or physics solving within this repository (XML generation and geometric contracts only).
- General-purpose robotics or non-human multi-body simulation outside human musculoskeletal movement templates.
- Native interactive 3D graphical user interface or rendering engine (external visualization tools consume the exported XML).
- Real-time motion capture telemetry ingestion or computer vision tracking pipelines.

## Features

| ID | Feature | Status | Tracking | Notes |
| --- | --- | --- | --- | --- |
| F1 | Back squat model generator | shipped | #171 | High-bar back squat builder in exercises.squat |
| F2 | Bench press model generator | shipped | #213 | Supine press builder in exercises.bench_press |
| F3 | Deadlift model generator | shipped | #133 | Conventional deadlift builder in exercises.deadlift |
| F4 | Snatch model generator | shipped | #171 | Wide-grip Olympic snatch builder in exercises.snatch |
| F5 | Clean and jerk model generator | shipped | #171 | Two-phase Olympic clean and jerk builder in exercises.clean_and_jerk |
| F6 | Baseline movement model generators | shipped | - | Non-barbell gait and sit-to-stand builders |
| F7 | Shared Olympic barbell component | shipped | - | Reusable IWF and IPF spec barbell model in shared.barbell |
| F8 | Shared musculoskeletal body component | shipped | #88 | Winter anthropometric full-body model in shared.body |
| F9 | Design-by-Contract validation suite | shipped | #118 | Runtime precondition and postcondition guards in shared.contracts |
| F10 | CLI model generation launcher | shipped | #264 | opensim-models console script and main entrypoint |
| F11 | UpstreamDrift model pack integration | shipped | #264 | Manifest model_pack.yaml and discovery entry point |
| F12 | Trajectory optimization helpers | shipped | #129 | Objective formulation and trajectory configs in optimization |
| F13 | Biomechanical visualization utilities | shipped | #210 | Model and kinematics plotting helpers in visualization |
| F14 | Cross-exercise parity testing suite | shipped | #119 | Biomechanical parameter parity validation in tests.parity |
| F15 | C4 architecture map contract | shipped | #344 | Mermaid C4 architecture contract enforced in CI |
| F16 | Rust acceleration core | parked | #120 | Experimental rust_core library unbuilt in standard CI |

## Links

- Status (generated): [`STATUS.md`](STATUS.md)
- Steward playbook: Repository_Management `docs/fleet-project-steward.md`
