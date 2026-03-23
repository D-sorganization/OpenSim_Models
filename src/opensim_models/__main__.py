"""CLI entry point: python -m opensim_models <exercise> [--output FILE] [--mass KG] [--height M] [--plates KG]."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from opensim_models.exercises.bench_press.bench_press_model import (
    build_bench_press_model,
)
from opensim_models.exercises.clean_and_jerk.clean_and_jerk_model import (
    build_clean_and_jerk_model,
)
from opensim_models.exercises.deadlift.deadlift_model import build_deadlift_model
from opensim_models.exercises.snatch.snatch_model import build_snatch_model
from opensim_models.exercises.squat.squat_model import build_squat_model

logger = logging.getLogger(__name__)

_BUILDERS = {
    "squat": build_squat_model,
    "bench_press": build_bench_press_model,
    "deadlift": build_deadlift_model,
    "snatch": build_snatch_model,
    "clean_and_jerk": build_clean_and_jerk_model,
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="opensim_models",
        description="Generate OpenSim .osim models for barbell exercises.",
    )
    parser.add_argument(
        "exercise",
        choices=sorted(_BUILDERS),
        help="Exercise to generate a model for.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output file path (default: <exercise>.osim in current directory).",
    )
    parser.add_argument(
        "--mass", type=float, default=80.0, help="Body mass in kg (default: 80)."
    )
    parser.add_argument(
        "--height",
        type=float,
        default=1.75,
        help="Body height in meters (default: 1.75).",
    )
    parser.add_argument(
        "--plates",
        type=float,
        default=60.0,
        help="Plate mass per side in kg (default: 60).",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable debug logging."
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Run the CLI."""
    args = _build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(name)s %(levelname)s: %(message)s",
    )

    builder = _BUILDERS[args.exercise]
    xml_str = builder(
        body_mass=args.mass,
        height=args.height,
        plate_mass_per_side=args.plates,
    )

    output_path = args.output or Path(f"{args.exercise}.osim")
    output_path.write_text(xml_str, encoding="utf-8")
    logger.info("Wrote %s", output_path)
    logger.warning("Generated %s (%d bytes)", output_path, len(xml_str))


if __name__ == "__main__":
    main(sys.argv[1:])
