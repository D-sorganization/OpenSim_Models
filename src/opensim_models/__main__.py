"""CLI entry point: python -m opensim_models <exercise> [--output FILE] [--mass KG] [--height M] [--plates KG]."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from opensim_models.exercises import EXERCISE_BUILDERS

logger = logging.getLogger(__name__)

_BUILDERS = EXERCISE_BUILDERS


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

    # DbC: validate numeric arguments before constructing any model objects
    if args.mass <= 0:
        sys.exit(f"--mass must be positive, got {args.mass}")
    if args.height <= 0:
        sys.exit(f"--height must be positive, got {args.height}")
    if args.plates < 0:
        sys.exit(f"--plates must be non-negative, got {args.plates}")

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(name)s %(levelname)s: %(message)s",
    )

    builder = _BUILDERS[args.exercise]
    # Gait and sit-to-stand models don't accept plate_mass_per_side
    _NO_BARBELL_EXERCISES = {"gait", "sit_to_stand"}
    if args.exercise in _NO_BARBELL_EXERCISES:
        xml_str = builder(body_mass=args.mass, height=args.height)
    else:
        xml_str = builder(
            body_mass=args.mass,
            height=args.height,
            plate_mass_per_side=args.plates,
        )

    output_path = args.output or Path(f"{args.exercise}.osim")
    output_path.write_text(xml_str, encoding="utf-8")
    logger.info("Wrote %s", output_path)
    logger.info("Generated %s (%d bytes)", output_path, len(xml_str))


if __name__ == "__main__":
    main(sys.argv[1:])
