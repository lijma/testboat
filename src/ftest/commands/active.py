"""ftest active — active version management (.ftest/.active)."""

from pathlib import Path

ACTIVE_FILE = ".active"
DEFAULT_VERSION = "draft"


def get_active_version(ftest_root: Path) -> str:
    """Return the currently active version name (default: 'draft')."""
    path = ftest_root / ".ftest" / ACTIVE_FILE
    if not path.exists():
        return DEFAULT_VERSION
    return path.read_text(encoding="utf-8").strip() or DEFAULT_VERSION


def set_active_version(ftest_root: Path, version: str) -> None:
    """Write the active version to .ftest/.active."""
    path = ftest_root / ".ftest" / ACTIVE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(version, encoding="utf-8")


def active_dir(ftest_root: Path) -> Path:
    """Return the path of the active version directory."""
    return ftest_root / ".ftest" / get_active_version(ftest_root)
