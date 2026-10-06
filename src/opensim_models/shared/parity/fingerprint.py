"""OpenSim engine adapter for the fleet ``model-fingerprint/v1`` standard.

Loads a generated exercise model in real OpenSim and measures raw engine-native
quantities; assembly, frame rotation and the CLI live in the vendored bundle.

    python -m opensim_models.shared.parity.fingerprint --all --out DIR
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.model_pack import list_exercises, manifest
from opensim_models.optimization.exercise_objectives import EXERCISE_OBJECTIVES
from opensim_models.shared.parity._canonical import (
    assemble,
    conformance,
    kinematics,
)

logger = logging.getLogger(__name__)

ENGINE = "opensim"

# Engine joint-coordinate name -> canonical name (only names that differ).
COORDINATE_ALIASES: dict[str, str] = {
    f"{joint}_{side}_{engine}": f"{joint}_{side}_{canonical}"
    for side in ("l", "r")
    for joint, engine, canonical in (
        ("wrist", "deviation", "deviate"),
        ("ankle", "inversion", "invert"),
    )
}

# Engine body name -> canonical segment (bodies are already canonical).
SEGMENT_ALIASES: dict[str, str] = {}

_FOOT_FORCE = "force_foot_l_heel_medial"


def _pelvis_root_joint(model: Any) -> str:
    """Return "free" if the pelvis hangs from a 6-DOF joint, else "fixed"."""
    joints = model.getJointSet()
    for i in range(joints.getSize()):
        joint = joints.get(i)
        if joint.getChildFrame().findBaseFrame().getName() == "pelvis":
            return "free" if joint.numCoordinates() == 6 else "fixed"
    return "fixed"


def _ground_friction(model: Any) -> dict[str, float] | None:
    import opensim

    forces = model.getForceSet()
    if forces.getIndex(_FOOT_FORCE, 0) < 0:
        return None
    force = opensim.SmoothSphereHalfSpaceForce.safeDownCast(forces.get(_FOOT_FORCE))
    return {
        "static": float(force.get_static_friction()),
        "dynamic": float(force.get_dynamic_friction()),
    }


def _load(exercise: str) -> tuple[Any, Any]:
    import opensim

    opensim.Logger.setLevelString("Error")
    xml = EXERCISE_BUILDERS[exercise]()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"{exercise}.osim"
        path.write_text(xml, encoding="utf-8")
        model = opensim.Model(str(path))
    return model, model.initSystem()


def _measure(model: Any, state: Any) -> tuple[dict[str, float], dict, dict]:
    """Return raw masses, coordinate limits and neutral world origins (Y-up)."""
    coords = model.getCoordinateSet()
    human = set(conformance.expected_coordinates(conformance.load_standard()))
    limits = {}
    for i in range(coords.getSize()):
        c = coords.get(i)
        # Root (pelvis_*) coordinates are not part of the 28 human coordinates.
        if COORDINATE_ALIASES.get(c.getName(), c.getName()) in human:
            limits[c.getName()] = (float(c.getRangeMin()), float(c.getRangeMax()))
        c.setValue(state, 0.0, False)
    model.realizePosition(state)
    masses, origins = {}, {}
    bodies = model.getBodySet()
    for i in range(bodies.getSize()):
        body = bodies.get(i)
        p = body.getPositionInGround(state)
        masses[body.getName()] = float(body.getMass())
        origins[body.getName()] = (p.get(0), p.get(1), p.get(2))
    return masses, limits, origins


def _rotation(model: Any, state: Any, body: str) -> list[list[float]]:
    model.realizePosition(state)
    rot = model.getBodySet().get(body).getTransformInGround(state).R()
    return [[rot.get(i, j) for j in range(3)] for i in range(3)]


def _coordinate_axes(
    model: Any, state: Any, std: dict[str, Any]
) -> dict[str, tuple[float, float, float]]:
    """Raw (engine-frame) rotation axis of every standard coordinate.

    Each coordinate alone goes from the all-zero pose to the probe angle; the
    axis is of its segment relative to the pelvis (``kinematics.segment_axis``).
    Precondition: *state* has every coordinate at 0 (as left by ``_measure``).
    """
    engine_name = {canon: raw for raw, canon in COORDINATE_ALIASES.items()}
    coords = model.getCoordinateSet()
    angle = kinematics.probe_angle_rad(std)
    out: dict[str, tuple[float, float, float]] = {}
    for coord, segment in kinematics.axis_probes(std).items():
        name = engine_name.get(coord, coord)
        before = _rotation(model, state, "pelvis"), _rotation(model, state, segment)
        coords.get(name).setValue(state, angle, False)
        after = _rotation(model, state, "pelvis"), _rotation(model, state, segment)
        coords.get(name).setValue(state, 0.0, False)
        out[name] = kinematics.segment_axis(*before, *after)
    return out


def fingerprint(exercise: str) -> dict[str, Any]:
    """Build *exercise*, load it in OpenSim and report what the engine sees.

    Raises:
        ValueError: if *exercise* is not a known exercise id.
    """
    import opensim

    if exercise not in EXERCISE_BUILDERS:
        raise ValueError(f"unknown exercise {exercise!r}")
    std = conformance.load_standard()
    version = str(opensim.GetVersion())
    try:
        model, state = _load(exercise)
        masses, limits, origins = _measure(model, state)
        axes = _coordinate_axes(model, state, std)
    except (RuntimeError, OSError) as exc:  # SWIG raises RuntimeError on bad models
        logger.error("OpenSim failed to load %s: %s", exercise, exc)
        return assemble.failed_fingerprint(ENGINE, version, exercise, exc)
    g = model.getGravity()
    objective = EXERCISE_OBJECTIVES.get(exercise)
    return assemble.assemble_fingerprint(
        engine=ENGINE,
        engine_version=version,
        exercise=exercise,
        std=std,
        root_joint=_pelvis_root_joint(model),
        gravity_engine=(g.get(0), g.get(1), g.get(2)),
        segment_masses_kg=masses,
        coordinate_limits_rad=limits,
        segment_origins_engine_m=origins,
        capabilities=assemble.capabilities_from_manifest(manifest(), std),
        coordinate_aliases=COORDINATE_ALIASES,
        segment_aliases=SEGMENT_ALIASES,
        ground_friction=_ground_friction(model),
        phase_count=None if objective is None else len(objective.phases),
        coordinate_axes_engine=axes,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point (shared bundle implementation)."""
    return assemble.run_fingerprint_cli(argv, fingerprint, list_exercises(), ENGINE)


if __name__ == "__main__":
    raise SystemExit(main())
