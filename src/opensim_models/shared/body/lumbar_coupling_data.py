"""Cited lumbar coupling laws, loaded from their single data source (#464, #473).

The per-level tables live only in ``lumbar_coupling_laws.json`` next to this
module (``LUMBAR_COUPLING_DATA``). This module validates that file and builds
``LumbarCouplingLaw`` objects from it; it holds no numbers of its own.

The shipped law is Xu et al. (2022), Front Surg 9:1002133,
doi:10.3389/fsurg.2022.1002133, Table 1, young group: in vivo per-level
rotation ranges, with each level's share of a motion taken as its fraction of
the summed range (a repository assumption, recorded in the data file).

Cross-repo note: publishing this section in the shared biomech parity
standard, so other packs can consume it, is Repository_Management board
proposal #2116; until it is decided the data file here is the only copy.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from functools import cache
from pathlib import Path
from typing import Any

from opensim_models.shared.body.lumbar_chain import (
    LUMBAR_LEVELS,
    LUMBAR_MOTIONS,
    LumbarCouplingLaw,
)

__all__ = [
    "LUMBAR_COUPLING_DATA",
    "XU2022_DOI",
    "XU2022_LAW_ID",
    "XU2022_YOUNG_LEVEL_ROM_DEG",
    "load_lumbar_coupling_laws",
    "lumbar_coupling_law",
    "xu2022_young_lumbar_law",
]

#: The single source of the cited per-level coupling data.
LUMBAR_COUPLING_DATA: Path = Path(__file__).with_name("lumbar_coupling_laws.json")

_SCHEMA_VERSION = 1
_DISTRIBUTIONS = frozenset({"proportional_to_level_rom"})
_REQUIRED = ("law_id", "version", "source", "doi", "distribution", "level_rom_deg")

XU2022_LAW_ID = "xu2022_young_rom_share"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _law_from_entry(entry: Mapping[str, Any]) -> LumbarCouplingLaw:
    """Build one law from a data-file entry (precondition: a JSON object)."""
    _require(isinstance(entry, Mapping), "each law must be a JSON object")
    for field in _REQUIRED:
        _require(field in entry, f"law entry is missing '{field}'")
    _require(
        entry["distribution"] in _DISTRIBUTIONS,
        f"unknown distribution {entry['distribution']!r}; "
        f"expected one of {sorted(_DISTRIBUTIONS)}",
    )
    return LumbarCouplingLaw.from_level_rom(
        entry["law_id"],
        entry["version"],
        entry["source"],
        entry["level_rom_deg"],
        doi=entry["doi"],
    )


def load_lumbar_coupling_laws(
    path: Path | None = None,
) -> dict[str, LumbarCouplingLaw]:
    """Load every cited law from *path* (default ``LUMBAR_COUPLING_DATA``).

    Preconditions (``ValueError``): the file's ``schema_version`` is supported,
    its ``levels`` and ``motions`` equal ``LUMBAR_LEVELS`` and
    ``LUMBAR_MOTIONS`` in order, it lists at least one law, law ids are unique
    and every entry passes the ``LumbarCouplingLaw`` contracts.
    Postcondition: a non-empty mapping of law id to law, in file order.
    """
    if path is None:
        return dict(_default_laws())
    return _load(path)


@cache
def _default_laws() -> tuple[tuple[str, LumbarCouplingLaw], ...]:
    return tuple(_load(LUMBAR_COUPLING_DATA).items())


def _load(path: Path) -> dict[str, LumbarCouplingLaw]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    _require(isinstance(data, Mapping), f"{path} must hold a JSON object")
    version = data.get("schema_version")
    _require(
        version == _SCHEMA_VERSION,
        f"unsupported schema_version {version!r}; expected {_SCHEMA_VERSION}",
    )
    _require(
        tuple(data.get("levels", ())) == LUMBAR_LEVELS,
        f"levels must be {list(LUMBAR_LEVELS)} (caudal first)",
    )
    _require(
        tuple(data.get("motions", ())) == tuple(LUMBAR_MOTIONS),
        f"motions must be {list(LUMBAR_MOTIONS)}",
    )
    entries = data.get("laws")
    _require(bool(entries) and isinstance(entries, list), "laws must be non-empty")
    laws: dict[str, LumbarCouplingLaw] = {}
    for entry in entries:
        law = _law_from_entry(entry)
        _require(law.law_id not in laws, f"duplicate law_id {law.law_id!r}")
        laws[law.law_id] = law
    return laws


def lumbar_coupling_law(law_id: str) -> LumbarCouplingLaw:
    """The cited law *law_id* from the data file (``KeyError`` if absent)."""
    laws = load_lumbar_coupling_laws()
    if law_id not in laws:
        raise KeyError(f"no lumbar coupling law {law_id!r}; known: {sorted(laws)}")
    return laws[law_id]


def xu2022_young_lumbar_law() -> LumbarCouplingLaw:
    """Coupling law from Xu et al. (2022) young-group per-level ranges."""
    return lumbar_coupling_law(XU2022_LAW_ID)


_XU2022 = xu2022_young_lumbar_law()
#: DOI of Xu et al. (2022), read from the data file.
XU2022_DOI: str = _XU2022.doi or ""
#: Xu 2022 Table 1, young group, degrees, caudal first (from the data file).
XU2022_YOUNG_LEVEL_ROM_DEG: dict[str, tuple[float, ...]] = {
    motion: tuple(values) for motion, values in (_XU2022.level_rom_deg or {}).items()
}
