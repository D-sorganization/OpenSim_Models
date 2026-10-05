"""Engine fingerprint: load a generated exercise model in real OpenSim.

Implements the ``model-fingerprint/v1`` schema of the fleet parity standard.
Every value is read from the model as OpenSim loaded it, never from this
package's Python constants.

CLI::

    python -m opensim_models.shared.parity.fingerprint --exercise squat
    python -m opensim_models.shared.parity.fingerprint --all --out DIR
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
import tempfile
from pathlib import Path
from typing import Any

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.model_pack import list_exercises, manifest
from opensim_models.optimization.exercise_objectives import EXERCISE_OBJECTIVES
from opensim_models.shared.parity._canonical import conformance

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


def _canonical_segment(body: str) -> str:
    return SEGMENT_ALIASES.get(body, body)


def _canonical_coordinate(coord: str) -> str:
    return COORDINATE_ALIASES.get(coord, coord)


def _pelvis_root_joint(model: Any) -> str:
    """Return "free" if the pelvis hangs from a 6-DOF joint, else "fixed"."""
    joints = model.getJointSet()
    for i in range(joints.getSize()):
        joint = joints.get(i)
        if joint.getChildFrame().findBaseFrame().getName() == "pelvis":
            return "free" if joint.numCoordinates() == 6 else "fixed"
    return "fixed"


def _read_segments(model: Any, std: dict[str, Any]) -> dict[str, dict[str, float]]:
    wanted = set(conformance.expected_segments(std))
    bodies = model.getBodySet()
    out: dict[str, dict[str, float]] = {}
    for i in range(bodies.getSize()):
        body = bodies.get(i)
        name = _canonical_segment(body.getName())
        if name in wanted:
            out[name] = {"mass_kg": float(body.getMass())}
    return out


def _read_coordinates(model: Any, std: dict[str, Any]) -> dict[str, dict[str, Any]]:
    wanted = set(conformance.expected_coordinates(std))
    coords = model.getCoordinateSet()
    out: dict[str, dict[str, Any]] = {}
    for i in range(coords.getSize()):
        coord = coords.get(i)
        name = _canonical_coordinate(coord.getName())
        if name in wanted:
            out[name] = {
                "limits_rad": [float(coord.getRangeMin()), float(coord.getRangeMax())]
            }
    return out


def _neutral_origins(
    model: Any, state: Any, std: dict[str, Any]
) -> dict[str, list[float]]:
    """World origin of each segment at all-zero coordinates, pelvis at origin."""
    coords = model.getCoordinateSet()
    for i in range(coords.getSize()):
        coords.get(i).setValue(state, 0.0, False)
    model.realizePosition(state)
    wanted = set(conformance.expected_segments(std))
    raw: dict[str, tuple[float, float, float]] = {}
    bodies = model.getBodySet()
    for i in range(bodies.getSize()):
        body = bodies.get(i)
        name = _canonical_segment(body.getName())
        if name in wanted:
            p = body.getPositionInGround(state)
            raw[name] = conformance.to_canonical(
                std, ENGINE, (p.get(0), p.get(1), p.get(2))
            )
    pelvis = raw["pelvis"]
    return {
        n: [float(a - b) for a, b in zip(v, pelvis, strict=True)]
        for n, v in raw.items()
    }


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


def _capabilities() -> dict[str, str]:
    caps = manifest().get("capabilities", {})
    return {key: str(entry["level"]) for key, entry in caps.items()}


def _load(exercise: str) -> tuple[Any, Any]:
    import opensim

    opensim.Logger.setLevelString("Error")
    xml = EXERCISE_BUILDERS[exercise]()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"{exercise}.osim"
        path.write_text(xml, encoding="utf-8")
        model = opensim.Model(str(path))
    return model, model.initSystem()


def fingerprint(exercise: str) -> dict[str, Any]:
    """Build *exercise*, load it in OpenSim and report what the engine sees.

    Raises:
        ValueError: if *exercise* is not a known exercise id.
    """
    import opensim

    if exercise not in EXERCISE_BUILDERS:
        raise ValueError(f"unknown exercise {exercise!r}")
    std = conformance.load_standard()
    fp: dict[str, Any] = {
        "schema": conformance.FINGERPRINT_SCHEMA,
        "engine": ENGINE,
        "engine_version": str(opensim.GetVersion()),
        "exercise": exercise,
        "standard_sha256": conformance.standard_sha256(),
        "loaded_in_engine": False,
        "load_error": None,
        "capabilities": _capabilities(),
    }
    try:
        model, state = _load(exercise)
        g = model.getGravity()
        segments = _read_segments(model, std)
        fp.update(
            root_joint=_pelvis_root_joint(model),
            gravity_canonical=list(
                conformance.to_canonical(std, ENGINE, (g.get(0), g.get(1), g.get(2)))
            ),
            body_mass_kg=sum(s["mass_kg"] for s in segments.values()),
            segments=segments,
            coordinates=_read_coordinates(model, std),
            segment_origins_neutral_m=_neutral_origins(model, state, std),
        )
        friction = _ground_friction(model)
        if friction is not None:
            fp["ground_friction"] = friction
        objective = EXERCISE_OBJECTIVES.get(exercise)
        if objective is not None:
            fp["phase_count"] = len(objective.phases)
        fp["loaded_in_engine"] = True
    except (RuntimeError, OSError) as exc:  # SWIG raises RuntimeError on bad models
        logger.error("OpenSim failed to load %s: %s", exercise, exc)
        fp["load_error"] = str(exc)
        return fp
    if not math.isfinite(fp["body_mass_kg"]):
        raise ValueError("fingerprint postcondition: body mass must be finite")
    return fp


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns a process exit code."""
    parser = argparse.ArgumentParser(description="OpenSim model-fingerprint/v1")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--exercise", choices=sorted(list_exercises()))
    group.add_argument("--all", action="store_true", help="fingerprint every exercise")
    parser.add_argument("--out", type=Path, default=None, help="output directory")
    args = parser.parse_args(argv)

    exercises = list_exercises() if args.all else [args.exercise]
    status = 0
    for exercise in exercises:
        fp = fingerprint(exercise)
        text = json.dumps(fp, indent=2, sort_keys=True)
        if args.out is None:
            sys.stdout.write(text + "\n")
        else:
            args.out.mkdir(parents=True, exist_ok=True)
            (args.out / f"{ENGINE}_{exercise}.json").write_text(
                text + "\n", encoding="utf-8"
            )
        if not fp["loaded_in_engine"]:
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
