#!/usr/bin/env python3
"""Generate all five exercise models with default anthropometrics.

Usage:
    python3 examples/generate_all_models.py [--output-dir OUTPUT_DIR]

Creates one .osim file per exercise in the specified output directory
(defaults to current working directory).
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from opensim_models.exercises import EXERCISE_BUILDERS

logger = logging.getLogger(__name__)

_EXERCISES = EXERCISE_BUILDERS


def main() -> None:
    """Generate all exercise models."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Directory to write .osim files (default: cwd)",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(name)s %(levelname)s: %(message)s",
    )

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, builder in _EXERCISES.items():
        xml_str = builder()
        out_path = output_dir / f"{name}.osim"
        out_path.write_text(xml_str, encoding="utf-8")
        print(f"Generated {out_path} ({len(xml_str)} bytes)")

    print(f"\nAll {len(_EXERCISES)} models generated in {output_dir}")


if __name__ == "__main__":
    main()
