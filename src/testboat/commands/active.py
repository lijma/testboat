"""testboat active — active version management (.testboat/.active)."""

from pathlib import Path

ACTIVE_FILE = ".active"
DEFAULT_VERSION = "draft"


def get_active_version(testboat_root: Path) -> str:
    """Return the currently active version name (default: 'draft')."""
    path = testboat_root / ".testboat" / ACTIVE_FILE
    if not path.exists():
        return DEFAULT_VERSION
    return path.read_text(encoding="utf-8").strip() or DEFAULT_VERSION


def set_active_version(testboat_root: Path, version: str) -> None:
    """Write the active version to .testboat/.active."""
    path = testboat_root / ".testboat" / ACTIVE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(version, encoding="utf-8")


def active_dir(testboat_root: Path) -> Path:
    """Return the path of the active version directory."""
    return testboat_root / ".testboat" / get_active_version(testboat_root)
