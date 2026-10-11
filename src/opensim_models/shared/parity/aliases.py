"""OpenSim coordinate names that differ from the canonical coordinate names.

Engine-free (no opensim import), so the optimization objectives and the
fingerprint share one table.
"""

from __future__ import annotations

# Engine joint-coordinate name -> canonical name (only names that differ).
COORDINATE_ALIASES: dict[str, str] = {
    f"{joint}_{side}_{engine}": f"{joint}_{side}_{canonical}"
    for side in ("l", "r")
    for joint, engine, canonical in (
        ("wrist", "deviation", "deviate"),
        ("ankle", "inversion", "invert"),
    )
}
# Inverse of the alias table: canonical coordinate name -> OpenSim name.
CANONICAL_TO_ENGINE: dict[str, str] = {v: k for k, v in COORDINATE_ALIASES.items()}


def engine_name(canonical: str) -> str:
    """OpenSim coordinate name of a canonical coordinate (identity if not aliased)."""
    return CANONICAL_TO_ENGINE.get(canonical, canonical)
