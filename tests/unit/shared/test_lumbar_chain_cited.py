"""Cited coupling law, physiological limits and mass conservation (#464).

The per-level values below are typed in independently from Xu et al. (2022),
Front Surg 9:1002133, doi:10.3389/fsurg.2022.1002133, Table 1, young group
(n = 14), rotation range about each motion's primary axis. They are checked
against the values shipped in ``lumbar_coupling_data``.
"""

from __future__ import annotations

import hashlib
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.exercises.base import ExerciseConfig
from opensim_models.exercises.deadlift.deadlift_model import DeadliftModelBuilder
from opensim_models.shared.body import BodyModelSpec, create_full_body
from opensim_models.shared.body.lumbar_chain import (
    LUMBAR_LEVELS,
    LumbarCouplingLaw,
    uniform_lumbar_law,
)
from opensim_models.shared.body.lumbar_coupling_data import (
    XU2022_DOI,
    load_lumbar_coupling_laws,
    xu2022_young_lumbar_law,
)
from opensim_models.shared.parity.standard import JOINT_LIMITS

pytestmark = pytest.mark.requires_opensim

try:
    import opensim
except ImportError:
    opensim = None

MOTIONS = ("flex", "lateral", "rotate")
LINKS = ("lumbar_L5", "lumbar_L4", "lumbar_L3", "lumbar_L2")
# XML numbers carry six decimals.
XML_TOL = 2e-6

# Xu 2022 Table 1, young group, degrees, caudal first (L5-S1 .. L1-L2).
XU_TABLE1_YOUNG = {
    "flex": (14.27, 10.08, 11.21, 7.92, 9.54),  # flexion-extension, ML axis
    "lateral": (8.55, 8.85, 8.79, 7.48, 11.34),  # left-right bend, AP axis
    "rotate": (8.03, 15.98, 16.88, 15.55, 15.17),  # left-right torsion, CC axis
}

# SHA-256 of every builder's default output, captured on origin/main
# (5e559d7) before the cited law and mass carving landed, re-pinned for the
# contact policy footprint and foot seating (#472). Change only for an
# intentional change to the default model.
DEFAULT_BUILD_SHA256 = {
    "bench_press": "3a5c3978afcaf7fea850465d579930efbb2cff07754dd0c1baecc1afbf4c6aeb",
    "clean_and_jerk": "b34c7005f3ac45458f7fcd84a82129c03dfa90b54a7c9d2fdade5575dce430e7",
    "deadlift": "9eb03cb867b8e8d3a664b003639f280d18f7b80116d38c09fc21c096913ebf26",
    "gait": "fcc1eb503c360d04529d2333e241cedc3043ea6d757f2c5b8df5dadd635e3494",
    "sit_to_stand": "9827f28d5f7115d6e293b237d7d4e70ab47a8c59c944b36580b0c945d064f317",
    "snatch": "33b0c1035537b6e69896b20875181a491dc93c059c1b5c0f8403c58e8560d66d",
    "squat": "cc1b79e5eb6d92f86986774bf1a92141cb39699558e84913baa66a5c0ae72f71",
}


def _bodies(law: LumbarCouplingLaw | None) -> dict[str, ET.Element]:
    bodyset, jointset = ET.Element("BodySet"), ET.Element("JointSet")
    kwargs = {}
    if law is not None:
        kwargs = {"lumbar_chain": law, "constraintset": ET.Element("ConstraintSet")}
    create_full_body(bodyset, jointset, BodyModelSpec(), **kwargs)
    return {b.get("name"): b for b in bodyset.findall("Body")}


def _vec(body: ET.Element, tag: str) -> np.ndarray:
    return np.array([float(v) for v in body.findtext(tag).split()])


def _mass(body: ET.Element) -> float:
    return float(body.findtext("mass"))


def _composite(bodies: list[ET.Element]) -> tuple[float, np.ndarray, np.ndarray]:
    """Mass, COM and diagonal inertia about the COM of co-located bodies."""
    mass = sum(_mass(b) for b in bodies)
    com = sum(_mass(b) * _vec(b, "mass_center") for b in bodies) / mass
    inertia = np.zeros(3)
    for b in bodies:
        d = _vec(b, "mass_center") - com
        parallel = _mass(b) * (np.dot(d, d) - d**2)
        inertia += _vec(b, "inertia")[:3] + parallel
    return mass, com, inertia


def _level_range(jointset: ET.Element, level: str, motion: str) -> tuple[float, ...]:
    joint = next(j for j in jointset if j.get("name") == f"lumbar_{level}")
    for coord in joint.find("coordinates"):
        if coord.get("name").startswith(f"lumbar_{motion}"):
            lo, hi = (float(v) for v in coord.findtext("range").split())
            if level == LUMBAR_LEVELS[0]:
                # The driver carries the total range; the level turns r_0 * q.
                ratio = xu2022_young_lumbar_law().ratios[motion][0]
                return ratio * lo, ratio * hi
            return lo, hi
    raise AssertionError(f"no {motion} coordinate at {level}")


class TestDefaultBitIdentical:
    @pytest.mark.parametrize("name", sorted(DEFAULT_BUILD_SHA256))
    def test_default_build_matches_pinned_sha256(self, name):
        digest = hashlib.sha256(EXERCISE_BUILDERS[name]().encode()).hexdigest()
        assert digest == DEFAULT_BUILD_SHA256[name]

    def test_every_builder_is_pinned(self):
        assert set(DEFAULT_BUILD_SHA256) == set(EXERCISE_BUILDERS)


class TestXu2022Law:
    def test_doi_and_provenance(self):
        law = xu2022_young_lumbar_law()
        assert XU2022_DOI == "10.3389/fsurg.2022.1002133"
        assert law.doi == XU2022_DOI
        assert XU2022_DOI in law.provenance
        assert "Xu" in law.source and "Table 1" in law.source

    def test_level_rom_matches_table_1(self):
        law = xu2022_young_lumbar_law()
        for motion in MOTIONS:
            assert law.level_rom_deg[motion] == XU_TABLE1_YOUNG[motion]

    @pytest.mark.parametrize("motion", MOTIONS)
    def test_ratios_are_shares_of_summed_level_rom(self, motion):
        law = xu2022_young_lumbar_law()
        total = math.fsum(XU_TABLE1_YOUNG[motion])
        for got, rom in zip(law.ratios[motion], XU_TABLE1_YOUNG[motion], strict=True):
            assert got == pytest.approx(rom / total, abs=1e-12)
        assert math.fsum(law.ratios[motion]) == pytest.approx(1.0, abs=1e-12)

    def test_builtin_laws_without_data_have_no_rom(self):
        assert uniform_lumbar_law().level_rom_deg is None
        assert uniform_lumbar_law().doi is None


class TestLawContracts:
    def _rom(self, **override):
        return {**XU_TABLE1_YOUNG, **override}

    @pytest.mark.parametrize("bad", [0.0, -1.0, float("nan"), float("inf")])
    def test_level_rom_must_be_positive_finite(self, bad):
        rom = self._rom(flex=(bad, 10.0, 11.0, 8.0, 9.0))
        with pytest.raises(ValueError):
            LumbarCouplingLaw.from_level_rom("x", "1", "src", rom)

    def test_level_rom_needs_five_levels(self):
        with pytest.raises(ValueError, match="5 levels"):
            LumbarCouplingLaw.from_level_rom(
                "x", "1", "src", self._rom(rotate=(1.0, 2.0))
            )

    def test_level_rom_needs_every_motion(self):
        rom = {k: v for k, v in XU_TABLE1_YOUNG.items() if k != "lateral"}
        with pytest.raises(ValueError, match="lateral"):
            LumbarCouplingLaw.from_level_rom("x", "1", "src", rom)

    @pytest.mark.parametrize("doi", ["", "fsurg.2022", "doi:10.1/x", "10.12/a b"])
    def test_doi_must_be_a_bare_doi(self, doi):
        with pytest.raises(ValueError, match="doi"):
            LumbarCouplingLaw.from_level_rom("x", "1", "src", XU_TABLE1_YOUNG, doi=doi)

    def test_ratios_must_be_proportional_to_level_rom(self):
        with pytest.raises(ValueError, match="proportional"):
            LumbarCouplingLaw(
                "x",
                "1",
                "src",
                uniform_lumbar_law().ratios,
                level_rom_deg=XU_TABLE1_YOUNG,
            )

    @pytest.mark.parametrize("bad", ["uniform", {"flex": (0.2,) * 5}, 1])
    def test_exercise_config_rejects_non_law(self, bad):
        with pytest.raises(TypeError, match="LumbarCouplingLaw"):
            ExerciseConfig(lumbar_chain=bad)

    def test_create_full_body_rejects_non_law(self):
        with pytest.raises(TypeError, match="LumbarCouplingLaw"):
            create_full_body(
                ET.Element("BodySet"),
                ET.Element("JointSet"),
                BodyModelSpec(),
                lumbar_chain="xu2022",  # type: ignore[arg-type]
                constraintset=ET.Element("ConstraintSet"),
            )


class TestCitedJointLimits:
    @pytest.mark.parametrize("motion", MOTIONS)
    def test_level_spans_are_proportional_to_cited_rom(self, motion):
        jointset = ET.Element("JointSet")
        create_full_body(
            ET.Element("BodySet"),
            jointset,
            BodyModelSpec(),
            lumbar_chain=xu2022_young_lumbar_law(),
            constraintset=ET.Element("ConstraintSet"),
        )
        lo, hi = JOINT_LIMITS[f"lumbar_{motion}"]
        total_rom = math.radians(math.fsum(XU_TABLE1_YOUNG[motion]))
        scale = (hi - lo) / total_rom
        sum_lo = sum_hi = 0.0
        for level, rom in zip(LUMBAR_LEVELS, XU_TABLE1_YOUNG[motion], strict=True):
            l_lo, l_hi = _level_range(jointset, level, motion)
            assert l_hi - l_lo == pytest.approx(scale * math.radians(rom), abs=1e-9)
            sum_lo, sum_hi = sum_lo + l_lo, sum_hi + l_hi
        assert (sum_lo, sum_hi) == pytest.approx((lo, hi), abs=1e-9)


class TestMassConservation:
    def test_total_body_mass_is_conserved(self):
        default = sum(_mass(b) for b in _bodies(None).values())
        chain = sum(_mass(b) for b in _bodies(xu2022_young_lumbar_law()).values())
        assert chain == pytest.approx(default, abs=XML_TOL * 6)

    @pytest.mark.parametrize("law", [uniform_lumbar_law(), xu2022_young_lumbar_law()])
    def test_lumbar_region_matches_lumped_torso(self, law):
        """Torso + link bodies equal the lumped torso in the neutral pose."""
        lumped = _composite([_bodies(None)["torso"]])
        chain_bodies = _bodies(law)
        carved = _composite([chain_bodies[n] for n in ("torso", *LINKS)])
        assert carved[0] == pytest.approx(lumped[0], abs=XML_TOL * 5)
        assert np.allclose(carved[1], lumped[1], atol=XML_TOL)
        assert np.allclose(carved[2], lumped[2], atol=XML_TOL * 5)

    def test_links_carry_positive_mass_carved_from_torso(self):
        default_torso = _mass(_bodies(None)["torso"])
        chain = _bodies(xu2022_young_lumbar_law())
        links = [_mass(chain[n]) for n in LINKS]
        assert all(m > 0.0 for m in links)
        assert _mass(chain["torso"]) == pytest.approx(
            default_torso - sum(links), abs=XML_TOL
        )


class TestMetadata:
    def test_model_records_doi(self):
        config = ExerciseConfig(lumbar_chain=xu2022_young_lumbar_law())
        root = ET.fromstring(DeadliftModelBuilder(config).build())
        assert XU2022_DOI in root.findtext(".//publications")


@pytest.mark.skipif(opensim is None, reason="opensim is not installed")
class TestOpenSimEngine:
    def _load(self, tmp_path: Path, config: ExerciseConfig | None) -> object:
        path = tmp_path / "model.osim"
        path.write_text(DeadliftModelBuilder(config).build(), encoding="utf-8")
        return opensim.Model(str(path))

    # Every law in the single data file (#473) must assemble in OpenSim.
    @pytest.mark.parametrize(
        "law", list(load_lumbar_coupling_laws().values()), ids=lambda law: law.law_id
    )
    def test_engine_mass_and_composed_rotation(self, tmp_path, law):
        default = self._load(tmp_path, None)
        default_state = default.initSystem()
        model = self._load(tmp_path, ExerciseConfig(lumbar_chain=law))
        state = model.initSystem()
        assert law.doi in model.get_publications()
        assert model.getTotalMass(state) == pytest.approx(
            default.getTotalMass(default_state), abs=1e-5
        )
        drivers = {"lumbar_flex": 0.4, "lumbar_lateral": -0.2, "lumbar_rotate": 0.3}
        coords = model.getCoordinateSet()
        for name, value in drivers.items():
            coords.get(name).setValue(state, value, False)
        model.assemble(state)
        model.realizePosition(state)
        for i, level in enumerate(LUMBAR_LEVELS[1:], start=1):
            for motion in MOTIONS:
                q = coords.get(f"lumbar_{motion}_{level}").getValue(state)
                expected = law.ratios[motion][i] * drivers[f"lumbar_{motion}"]
                assert q == pytest.approx(expected, abs=1e-9)
        pelvis = model.getBodySet().get("pelvis")
        torso = model.getBodySet().get("torso")
        # Keep the Transform alive: R() is a reference into it, and reading
        # the matrix off a temporary is a dangling read (uninitialised memory).
        transform = torso.findTransformBetween(state, pelvis)
        rot = transform.R()
        got = np.array([[rot.get(r, c) for c in range(3)] for r in range(3)])
        assert np.allclose(got, _expected_rotation(law, drivers), atol=1e-9)


def _axis_rotation(axis: tuple[float, float, float], angle: float) -> np.ndarray:
    a = np.array(axis, float)
    k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(angle) * k + (1 - math.cos(angle)) * (k @ k)


def _expected_rotation(law: LumbarCouplingLaw, drivers: dict[str, float]):
    """Caudal-first product of per-level rotations, pelvis to torso."""
    axes = {"flex": (0, 0, -1), "lateral": (-1, 0, 0), "rotate": (0, 1, 0)}
    total = np.eye(3)
    for i in range(len(LUMBAR_LEVELS)):
        for motion in MOTIONS:
            angle = law.ratios[motion][i] * drivers[f"lumbar_{motion}"]
            total = total @ _axis_rotation(axes[motion], angle)
    return total
