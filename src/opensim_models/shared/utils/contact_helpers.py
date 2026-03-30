"""Contact geometry and force helpers for OpenSim .osim files.

DRY: Contact geometry (half-spaces, spheres) and Hunt-Crossley forces
are defined here and reused by exercise model builders.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

from opensim_models.shared.utils.xml_helpers import vec3_str

logger = logging.getLogger(__name__)


def add_contact_half_space(
    model: ET.Element,
    *,
    name: str = "ground_contact",
    body: str = "ground",
    location: tuple[float, float, float] = (0, 0, 0),
    orientation: tuple[float, float, float] = (0, 0, -1.5708),
) -> ET.Element:
    """Add a ContactHalfSpace geometry to the model's ContactGeometrySet.

    The default orientation (-90 deg about Z) makes the half-space surface
    point in the +Y direction, which is the standard ground normal in OpenSim.
    """
    cg_set = model.find("ContactGeometrySet")
    if cg_set is None:
        cg_set = ET.SubElement(model, "ContactGeometrySet")
    geom = ET.SubElement(cg_set, "ContactHalfSpace", name=name)
    ET.SubElement(geom, "socket_frame").text = (
        f"/bodyset/{body}" if body != "ground" else "/ground"
    )
    ET.SubElement(geom, "location").text = vec3_str(*location)
    ET.SubElement(geom, "orientation").text = vec3_str(*orientation)
    return geom


def add_contact_sphere(
    model: ET.Element,
    *,
    name: str,
    body: str,
    location: tuple[float, float, float],
    radius: float = 0.02,
) -> ET.Element:
    """Add a ContactSphere geometry for foot contact points."""
    if radius <= 0:
        raise ValueError(f"Contact sphere radius must be positive, got {radius}")
    cg_set = model.find("ContactGeometrySet")
    if cg_set is None:
        cg_set = ET.SubElement(model, "ContactGeometrySet")
    geom = ET.SubElement(cg_set, "ContactSphere", name=name)
    ET.SubElement(geom, "socket_frame").text = f"/bodyset/{body}"
    ET.SubElement(geom, "location").text = vec3_str(*location)
    ET.SubElement(geom, "radius").text = f"{radius:.6f}"
    return geom


def add_hunt_crossley_force(
    model: ET.Element,
    *,
    name: str,
    contact_geometry_1: str,
    contact_geometry_2: str,
    stiffness: float = 1e7,
    dissipation: float = 0.5,
    static_friction: float = 0.8,
    dynamic_friction: float = 0.6,
    viscous_friction: float = 0.2,
) -> ET.Element:
    """Add a HuntCrossleyForce between two contact geometries."""
    force_set = model.find("ForceSet")
    if force_set is None:
        force_set = ET.SubElement(model, "ForceSet")
    force = ET.SubElement(force_set, "HuntCrossleyForce", name=name)
    ET.SubElement(force, "contact_geometry_1").text = contact_geometry_1
    ET.SubElement(force, "contact_geometry_2").text = contact_geometry_2
    ET.SubElement(force, "stiffness").text = f"{stiffness:.1f}"
    ET.SubElement(force, "dissipation").text = f"{dissipation:.6f}"
    ET.SubElement(force, "static_friction").text = f"{static_friction:.6f}"
    ET.SubElement(force, "dynamic_friction").text = f"{dynamic_friction:.6f}"
    ET.SubElement(force, "viscous_friction").text = f"{viscous_friction:.6f}"
    return force
