"""Model-pack manifest entry point for UpstreamDrift integration.

Implements the ``biomech.model_pack`` entry-point API consumed by
UpstreamDrift (umbrella: D-sorganization/UpstreamDrift#5179, schema:
D-sorganization/UpstreamDrift#5199). The manifest is shipped as
``model_pack.yaml`` at the package root and validates against the
``model_pack/v1`` schema.

Public API (all importable as ``opensim_models.model_pack``):

* :func:`resolve` -- absolute :class:`~pathlib.Path` to the exercises directory.
* :func:`manifest` -- parsed manifest as a :class:`dict`.
* :func:`list_exercises` -- list of exercise IDs declared by the manifest.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from opensim_models._messages import (
    ERR_MANIFEST_MISSING,
    ERR_MODELS_ROOT_MISSING,
)

# Manifest is shipped at the repo root, two parents above this file
# (``src/opensim_models/model_pack.py`` -> ``<repo>/model_pack.yaml``).
# When installed as a wheel the same file is bundled at the package root
# (``opensim_models/model_pack.yaml``) via the hatch ``force-include``
# directive in ``pyproject.toml``.
_PACKAGE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PACKAGE_DIR.parent.parent
_MANIFEST_CANDIDATES = (
    _REPO_ROOT / "model_pack.yaml",
    _PACKAGE_DIR / "model_pack.yaml",
)


def _find_manifest_path() -> Path:
    """Return the first manifest path that exists on disk.

    Searches the repo-root location first (editable install / source
    checkout) and then the in-package copy (wheel install).
    """
    for candidate in _MANIFEST_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        ERR_MANIFEST_MISSING.format(
            paths=", ".join(str(p) for p in _MANIFEST_CANDIDATES),
        )
    )


@lru_cache(maxsize=1)
def manifest() -> dict[str, Any]:
    """Return the parsed ``model_pack.yaml`` manifest.

    Returns:
        Mapping with keys defined by the ``model_pack/v1`` schema
        (``schema``, ``repo``, ``package``, ``engine``, ``engine_version``,
        ``anthropometrics``, ``format``, ``models_root``, ``exercises``).
    """
    path = _find_manifest_path()
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(
            ERR_MANIFEST_MISSING.format(paths=str(path)),
        )
    return data


def resolve() -> Path:
    """Return the absolute :class:`~pathlib.Path` to the exercises directory.

    The path resolves relative to the manifest file: in a source checkout
    it points at ``<repo>/src/opensim_models/exercises``; when installed
    from a wheel it points at the bundled package's ``exercises`` directory.
    """
    data = manifest()
    models_root = data["models_root"]
    base = _find_manifest_path().parent
    candidate = (base / models_root).resolve()
    if candidate.is_dir():
        return candidate
    # Wheel install: the manifest sits next to the package, and the
    # ``models_root`` path is repo-relative. Fall back to the package's
    # built-in ``exercises`` directory.
    fallback = (_PACKAGE_DIR / "exercises").resolve()
    if fallback.is_dir():
        return fallback
    raise FileNotFoundError(
        ERR_MODELS_ROOT_MISSING.format(path=str(candidate)),
    )


def list_exercises() -> list[str]:
    """Return the list of exercise IDs declared by the manifest."""
    return [entry["id"] for entry in manifest().get("exercises", [])]


__all__ = ["list_exercises", "manifest", "resolve"]
