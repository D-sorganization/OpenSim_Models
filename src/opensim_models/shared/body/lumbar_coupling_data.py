"""Published per-level lumbar ranges of motion and the law built from them (#464).

Source (open access, CC BY 4.0), checked against the full text on Europe PMC
(PMC9643460):

    Xu F, Zhou S, Li Z, Jiang S, Chen Z, Sun Z, Li W. The 6 degrees-of-freedom
    range of motion of the L1-S1 vertebrae in young and middle-aged
    asymptomatic people. Front Surg. 2022;9:1002133.
    doi:10.3389/fsurg.2022.1002133

In vivo dual-fluoroscopic, CT-model-matched intervertebral rotation ranges of
asymptomatic volunteers. The values below are Table 1, young group (n = 14,
20-30 years), mean range in degrees about each motion's primary axis:

* flexion-extension: mediolateral (ML) axis, postures 45 deg trunk flexion
  to maximal extension (so the flexion range is not the maximal one);
* left-right bend: anteroposterior (AP) axis, maximal bending to each side;
* left-right torsion: craniocaudal (CC) axis, maximal twisting to each side.

Assumptions of this repository (not published results):

* motion is shared across levels in proportion to each level's range, so the
  coupling ratios are ``range_i / sum(range)`` (``from_level_rom``);
* the shares are taken from the young cohort's means; inter-subject SDs are
  large (Table 1) and are not used;
* level limits are the cited ranges scaled to the parity-standard total range
  of the driver coordinate (``lumbar_chain``), one factor per motion.

Cross-repo note: UpstreamDrift's segmental-spine work (SPN-3) carries its own
cited laws; when a shared package exists this table should move there.
"""

from __future__ import annotations

from opensim_models.shared.body.lumbar_chain import LumbarCouplingLaw

__all__ = [
    "XU2022_DOI",
    "XU2022_YOUNG_LEVEL_ROM_DEG",
    "xu2022_young_lumbar_law",
]

XU2022_DOI = "10.3389/fsurg.2022.1002133"

_XU2022_SOURCE = (
    "Xu F, Zhou S, Li Z, Jiang S, Chen Z, Sun Z, Li W. Front Surg 9:1002133 "
    "(2022), Table 1, young group (n=14), per-level primary-axis rotation "
    "range; shares proportional to range (repository assumption)"
)

#: Xu 2022 Table 1, young group, degrees, caudal first (L5/S1 .. L1/L2).
XU2022_YOUNG_LEVEL_ROM_DEG: dict[str, tuple[float, ...]] = {
    # Flexion-extension, ML axis: L5-S1, L4-L5, L3-L4, L2-L3, L1-L2.
    "flex": (14.27, 10.08, 11.21, 7.92, 9.54),
    # Left-right bend, AP axis.
    "lateral": (8.55, 8.85, 8.79, 7.48, 11.34),
    # Left-right torsion, CC axis.
    "rotate": (8.03, 15.98, 16.88, 15.55, 15.17),
}


def xu2022_young_lumbar_law() -> LumbarCouplingLaw:
    """Coupling law from Xu et al. (2022) young-group per-level ranges."""
    return LumbarCouplingLaw.from_level_rom(
        "xu2022_young_rom_share",
        "1",
        _XU2022_SOURCE,
        XU2022_YOUNG_LEVEL_ROM_DEG,
        doi=XU2022_DOI,
    )
