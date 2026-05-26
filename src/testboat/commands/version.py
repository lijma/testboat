"""testboat version — snapshot and manage named test artifact versions."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from testboat.commands.active import DEFAULT_VERSION, get_active_version, set_active_version

DRAFT_DIR = "draft"
VERSION_META = ".version.yaml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _testboat_root_dir(testboat_root: Path) -> Path:
    return testboat_root / ".testboat"


def _draft_path(testboat_root: Path) -> Path:
    return _testboat_root_dir(testboat_root) / DRAFT_DIR


def _version_path(testboat_root: Path, version: str) -> Path:
    return _testboat_root_dir(testboat_root) / version


def _list_versions(testboat_root: Path) -> list[str]:
    """Return sorted list of existing version names (excludes draft)."""
    testboat_dir = _testboat_root_dir(testboat_root)
    if not testboat_dir.exists():
        return []
    return sorted(
        d.name for d in testboat_dir.iterdir()
        if d.is_dir() and d.name != DRAFT_DIR and not d.name.startswith(".")
    )


def _write_meta(version_dir: Path, version: str, base: str | None) -> None:
    meta = {
        "version": version,
        "base": base,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    (version_dir / VERSION_META).write_text(
        yaml.dump(meta, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def _read_meta(version_dir: Path) -> dict[str, Any]:
    meta_path = version_dir / VERSION_META
    if not meta_path.exists():
        return {}
    return yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

def create_version(testboat_root: Path, version: str, base: str | None = None) -> Path:
    """Create a new named version.

    If *base* is None: copy draft → .testboat/<version>/
    If *base* is set:  copy .testboat/<base>/ → .testboat/<version>/

    Returns the created version directory.
    Raises FileExistsError if version already exists.
    Raises FileNotFoundError if base version or draft does not exist.
    Raises ValueError if version name is 'draft' or starts with '.'.
    """
    if version == DRAFT_DIR or version.startswith("."):
        raise ValueError(f"Invalid version name '{version}'.")

    dest = _version_path(testboat_root, version)
    if dest.exists():
        raise FileExistsError(f"Version '{version}' already exists.")

    if base is None:
        src = _draft_path(testboat_root)
        if not src.exists():
            raise FileNotFoundError("No draft found. Run `testboat init` first.")
    else:
        src = _version_path(testboat_root, base)
        if not src.exists():
            raise FileNotFoundError(f"Base version '{base}' not found.")

    shutil.copytree(src, dest)
    _write_meta(dest, version, base)
    return dest


def list_versions(testboat_root: Path) -> list[dict[str, Any]]:
    """Return list of version info dicts, sorted by name."""
    result = []
    for name in _list_versions(testboat_root):
        vdir = _version_path(testboat_root, name)
        meta = _read_meta(vdir)
        cases = len(list((vdir / "cases").glob("TC-*.yaml"))) if (vdir / "cases").exists() else 0
        bugs = len(list((vdir / "bugs").glob("BUG-*.yaml"))) if (vdir / "bugs").exists() else 0
        result.append({
            "version": name,
            "base": meta.get("base"),
            "created_at": meta.get("created_at", ""),
            "cases": cases,
            "bugs": bugs,
        })
    return result


def switch_version(testboat_root: Path, version: str) -> str:
    """Set the active version. Returns the version name.

    Raises FileNotFoundError if version != 'draft' and directory doesn't exist.
    """
    if version != DEFAULT_VERSION:
        vdir = _version_path(testboat_root, version)
        if not vdir.exists():
            raise FileNotFoundError(f"Version '{version}' not found.")
    set_active_version(testboat_root, version)
    return version


def get_current_active(testboat_root: Path) -> str:
    """Return the currently active version name."""
    return get_active_version(testboat_root)


def show_version(testboat_root: Path, version: str) -> dict[str, Any]:
    """Return version info. Raises FileNotFoundError if not found."""
    vdir = _version_path(testboat_root, version)
    if not vdir.exists():
        raise FileNotFoundError(f"Version '{version}' not found.")
    meta = _read_meta(vdir)
    cases = len(list((vdir / "cases").glob("TC-*.yaml"))) if (vdir / "cases").exists() else 0
    bugs = len(list((vdir / "bugs").glob("BUG-*.yaml"))) if (vdir / "bugs").exists() else 0
    executions = len(list((vdir / "executions" / "results").glob("RES-*.yaml"))) \
        if (vdir / "executions" / "results").exists() else 0
    return {
        "version": version,
        "base": meta.get("base"),
        "created_at": meta.get("created_at", ""),
        "cases": cases,
        "bugs": bugs,
        "results": executions,
    }
