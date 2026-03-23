# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-22

### Added

- Five exercise model builders: squat, bench press, deadlift, snatch, clean and jerk.
- Full-body musculoskeletal model with 15 segments and bilateral limbs.
- Olympic barbell model (men's and women's specifications).
- Design-by-Contract precondition and postcondition checks.
- Geometry utilities: cylinder, rectangular prism, sphere inertia; parallel axis theorem.
- CLI entry point: `python -m opensim_models <exercise>`.
- Hypothesis property-based tests for geometry and anthropometric invariants.
- Edge-case tests for boundary conditions and invalid inputs.
- Benchmark tests for model generation performance.
- CI pipeline with Python 3.10-3.12 matrix, security scanning, and coverage gates.
- CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md.
- Docker multi-stage build (builder, runtime, training).
- Dependabot configuration for automated dependency updates.
- Example script for batch model generation.

### Changed

- Postcondition errors now raise `ValueError` instead of `AssertionError`.
- Pelvis height is derived from anthropometric data (thigh + shank + foot lengths).
- All exercises with hand-held barbells use bilateral (both hands) attachment.
- Removed unused `joint_type` parameter from model builders.
- Removed phantom dependencies (scipy, lxml) from requirements.

### Security

- CI uses pinned action versions with SHA hashes.
- Bandit security scanning enabled.
- pip-audit for dependency vulnerability checking.
