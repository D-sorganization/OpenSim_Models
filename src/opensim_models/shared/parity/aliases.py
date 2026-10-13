"""OpenSim coordinate names that differ from the canonical coordinate names.

Engine-free (no opensim import), so the optimization objectives and the
fingerprint share one table.
"""

from __future__ import annotations

# Engine joint-coordinate name -> canonical name (only names that differ).
# Following OpenSim_Models#396, all coordinate names match the canonical set.
COORDINATE_ALIASES: dict[str, str] = {}
# Inverse of the alias table: canonical coordinate name -> OpenSim name.
CANONICAL_TO_ENGINE: dict[str, str] = {}


def engine_name(canonical: str) -> str:
    """OpenSim coordinate name of a canonical coordinate (identity if not aliased)."""
    return CANONICAL_TO_ENGINE.get(canonical, canonical)
