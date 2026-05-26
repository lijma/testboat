"""ftest tag — manage sprint / type / module tag registry."""

from __future__ import annotations
from ftest.commands.active import active_dir

from pathlib import Path
from typing import Literal

import yaml

TAGS_FILE = "tags.yaml"
TAGS_DIR = ""

TagKind = Literal["sprint", "type", "module"]
TAG_KINDS: tuple[TagKind, ...] = ("sprint", "type", "module")

DEFAULT_TAGS: dict[str, list[str]] = {
    "sprint": [],
    "type": [
        "functional",
        "regression",
        "smoke",
        "performance",
        "security",
        "accessibility",
        "exploratory",
    ],
    "module": [],
}


def _tags_path(ftest_root: Path) -> Path:
    return active_dir(ftest_root) /  TAGS_FILE


def _load(ftest_root: Path) -> dict[str, list[str]]:
    path = _tags_path(ftest_root)
    if not path.exists():
        return {k: list(v) for k, v in DEFAULT_TAGS.items()}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    # ensure all kinds present
    for kind in TAG_KINDS:
        data.setdefault(kind, [])
    return data


def _save(ftest_root: Path, data: dict[str, list[str]]) -> None:
    path = _tags_path(ftest_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def add_tag(ftest_root: Path, kind: str, value: str) -> bool:
    """Add *value* to *kind* tag list.

    Returns True if added, False if already existed.
    Raises ValueError for unknown kind.
    """
    if kind not in TAG_KINDS:
        raise ValueError(f"Unknown tag kind '{kind}'. Supported: {', '.join(TAG_KINDS)}")
    data = _load(ftest_root)
    if value in data[kind]:
        return False
    data[kind].append(value)
    _save(ftest_root, data)
    return True


def list_tags(ftest_root: Path) -> dict[str, list[str]]:
    """Return all tags grouped by kind."""
    return _load(ftest_root)


def tag_exists(ftest_root: Path, kind: str, value: str) -> bool:
    """Return True if *value* exists under *kind*."""
    data = _load(ftest_root)
    return value in data.get(kind, [])


def init_tags(ftest_root: Path) -> Path:
    """Write default tags.yaml (idempotent). Returns file path."""
    path = _tags_path(ftest_root)
    if not path.exists():
        _save(ftest_root, {k: list(v) for k, v in DEFAULT_TAGS.items()})
    return path
