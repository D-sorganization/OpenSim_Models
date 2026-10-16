"""Full-body musculoskeletal model builder.

Builds a 15-segment body (pelvis, torso, head, bilateral arms and legs)
with appropriate joint types. Anthropometric defaults follow Winter (2009)
for a 50th-percentile male (height=1.75 m, mass=80 kg).

Law of Demeter: exercise modules call create_full_body() and receive
body/joint elements -- they never manipulate segment internals.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

from opensim_models.shared.body._segment_data import BodyModelSpec
from opensim_models.shared.body.appendicular import (
    SHOULDER_ADDUCT_RANGE,
    WRIST_DEVIATE_RANGE,
    WRIST_DEVIATION_RANGE,
    add_lower_limbs,
    add_upper_limbs,
)
from opensim_models.shared.body.axial_skeleton import add_axial_body, add_axial_joints
from opensim_models.shared.body.lumbar_chain import (
    LumbarCouplingLaw,
    add_lumbar_chain_bodies,
    require_lumbar_law,
)

logger = logging.getLogger(__name__)

__all__ = [
    "BodyModelSpec",
    "SHOULDER_ADDUCT_RANGE",
    "WRIST_DEVIATE_RANGE",
    "WRIST_DEVIATION_RANGE",
    "create_full_body",
]


def create_full_body(
    bodyset: ET.Element,
    jointset: ET.Element,
    spec: BodyModelSpec | None = None,
    *,
    skip_ground_joint: bool = False,
    lumbar_chain: LumbarCouplingLaw | None = None,
    constraintset: ET.Element | None = None,
) -> dict[str, ET.Element]:
    """Build the full-body model and append bodies/joints to the given sets.

    Args:
        bodyset: XML element to append Body elements to.
        jointset: XML element to append Joint elements to.
        spec: Anthropometric specification (defaults to 50th-percentile male).
        skip_ground_joint: When True, the FreeJoint connecting pelvis to ground
            is omitted (use when another joint provides the pelvis parent).
        lumbar_chain: Opt-in coupling law. When given, the single lumbar joint
            is replaced by the five-level segmental chain (#464); ``None``
            (default) leaves the model unchanged.
        constraintset: ConstraintSet receiving the chain's coupler constraints;
            required when ``lumbar_chain`` is given.

    Raises TypeError when ``lumbar_chain`` is not a ``LumbarCouplingLaw`` and
    ValueError when it is given without ``constraintset``.

    Returns dict of body name -> ET.Element for all created bodies.
    """
    if spec is None:
        spec = BodyModelSpec()
    require_lumbar_law(lumbar_chain)
    if lumbar_chain is not None and constraintset is None:
        raise ValueError("lumbar_chain requires a constraintset")

    logger.info(
        "Building full-body model (mass=%.1f kg, height=%.2f m)",
        spec.total_mass,
        spec.height,
    )

    bodies: dict[str, ET.Element] = {}

    # --- Axial skeleton (pelvis, torso, head) ---
    _, p_len, p_rad = add_axial_body(bodyset, spec, "pelvis", bodies)
    _, t_len, t_rad = add_axial_body(bodyset, spec, "torso", bodies)
    add_axial_body(bodyset, spec, "head", bodies)
    if lumbar_chain is not None:
        add_lumbar_chain_bodies(bodyset, bodies)
    add_axial_joints(
        jointset,
        spec,
        p_len,
        t_len,
        skip_ground_joint=skip_ground_joint,
        lumbar_chain=lumbar_chain,
        constraintset=constraintset,
    )

    # --- Upper limbs ---
    add_upper_limbs(bodyset, jointset, spec, t_len, t_rad, bodies)

    # --- Lower limbs ---
    add_lower_limbs(bodyset, jointset, spec, p_len, p_rad, bodies)

    logger.info("Full-body model complete: %d bodies created", len(bodies))
    return bodies
