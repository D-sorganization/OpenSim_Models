"""The lumbar coupling data has exactly one source (#473).

Every cited per-level table lives in ``lumbar_coupling_laws.json``. Python code
loads laws from that file; no ``src/`` module may carry the numbers itself.
The independent transcription in ``test_lumbar_chain_cited.py`` is a test
oracle against the paper, not a source the models consume.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import opensim_models
from opensim_models.shared.body.lumbar_chain import LUMBAR_LEVELS, LUMBAR_MOTIONS
from opensim_models.shared.body.lumbar_coupling_data import (
    LUMBAR_COUPLING_DATA,
    XU2022_DOI,
    XU2022_LAW_ID,
    XU2022_YOUNG_LEVEL_ROM_DEG,
    load_lumbar_coupling_laws,
    xu2022_young_lumbar_law,
)

PACKAGE_ROOT = Path(opensim_models.__file__).parent


def _raw() -> dict:
    return json.loads(LUMBAR_COUPLING_DATA.read_text(encoding="utf-8"))


def _write(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "laws.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class TestSingleSource:
    def test_data_file_ships_inside_the_package(self):
        assert LUMBAR_COUPLING_DATA.is_file()
        assert PACKAGE_ROOT in LUMBAR_COUPLING_DATA.parents

    def test_no_python_module_carries_the_cited_numbers(self):
        """Any per-level value literal in src/*.py is a second copy."""
        values = {
            f"{v:g}"
            for law in _raw()["laws"]
            for row in law["level_rom_deg"].values()
            for v in row
        }
        pattern = re.compile(
            r"(?<![\w.])(" + "|".join(re.escape(v) for v in values) + r")(?![\w.])"
        )
        offenders = [
            str(path.relative_to(PACKAGE_ROOT))
            for path in PACKAGE_ROOT.rglob("*.py")
            if pattern.search(path.read_text(encoding="utf-8"))
        ]
        assert offenders == []

    def test_xu_law_is_the_law_loaded_from_the_data_file(self):
        assert load_lumbar_coupling_laws()[XU2022_LAW_ID] == xu2022_young_lumbar_law()

    def test_public_constants_are_derived_from_the_data_file(self):
        entry = next(law for law in _raw()["laws"] if law["law_id"] == XU2022_LAW_ID)
        assert entry["doi"] == XU2022_DOI
        assert {m: list(v) for m, v in XU2022_YOUNG_LEVEL_ROM_DEG.items()} == entry[
            "level_rom_deg"
        ]

    def test_every_law_is_cited(self):
        for law in load_lumbar_coupling_laws().values():
            assert law.doi is not None
            assert law.level_rom_deg is not None

    def test_file_declares_the_chain_convention(self):
        raw = _raw()
        assert tuple(raw["levels"]) == LUMBAR_LEVELS
        assert tuple(raw["motions"]) == tuple(LUMBAR_MOTIONS)


class TestLoaderContracts:
    def test_rejects_unknown_schema_version(self, tmp_path):
        with pytest.raises(ValueError, match="schema_version"):
            load_lumbar_coupling_laws(
                _write(tmp_path, {**_raw(), "schema_version": 99})
            )

    def test_rejects_level_order_mismatch(self, tmp_path):
        data = {**_raw(), "levels": list(reversed(LUMBAR_LEVELS))}
        with pytest.raises(ValueError, match="levels"):
            load_lumbar_coupling_laws(_write(tmp_path, data))

    def test_rejects_motion_mismatch(self, tmp_path):
        data = {**_raw(), "motions": ["flex", "lateral"]}
        with pytest.raises(ValueError, match="motions"):
            load_lumbar_coupling_laws(_write(tmp_path, data))

    def test_rejects_duplicate_law_id(self, tmp_path):
        raw = _raw()
        data = {**raw, "laws": raw["laws"] * 2}
        with pytest.raises(ValueError, match="duplicate"):
            load_lumbar_coupling_laws(_write(tmp_path, data))

    def test_rejects_unknown_distribution(self, tmp_path):
        raw = _raw()
        law = {**raw["laws"][0], "distribution": "made_up"}
        with pytest.raises(ValueError, match="distribution"):
            load_lumbar_coupling_laws(_write(tmp_path, {**raw, "laws": [law]}))

    @pytest.mark.parametrize("field", ["law_id", "version", "source", "doi"])
    def test_rejects_missing_field(self, tmp_path, field):
        raw = _raw()
        law = {k: v for k, v in raw["laws"][0].items() if k != field}
        with pytest.raises(ValueError, match=field):
            load_lumbar_coupling_laws(_write(tmp_path, {**raw, "laws": [law]}))

    def test_rejects_empty_law_list(self, tmp_path):
        with pytest.raises(ValueError, match="laws"):
            load_lumbar_coupling_laws(_write(tmp_path, {**_raw(), "laws": []}))

    def test_law_contracts_still_apply(self, tmp_path):
        raw = _raw()
        rom = {**raw["laws"][0]["level_rom_deg"], "flex": [1.0, 2.0]}
        law = {**raw["laws"][0], "level_rom_deg": rom}
        with pytest.raises(ValueError, match="5 levels"):
            load_lumbar_coupling_laws(_write(tmp_path, {**raw, "laws": [law]}))
