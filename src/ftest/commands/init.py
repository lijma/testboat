"""ftest init — initialise .ftest/ runtime directory in the workspace."""

from pathlib import Path

import yaml

from ftest.commands.active import DEFAULT_VERSION, set_active_version

FTEST_DIR = ".ftest"
DRAFT_DIR = "draft"

DRAFT_SUBDIRS = [
    "strategy",
    "cases",
    "executions",
    "bugs",
    "reports",
]


def _default_config(workspace: Path) -> dict:
    return {
        "version": "draft",
        "workspace": str(workspace),
        "created_by": "ftest init",
    }


def init_workspace(workspace: Path) -> Path:
    """Create (or refresh) .ftest/draft/ structure under *workspace*.

    Idempotent: safe to run multiple times. Returns the .ftest path.
    """
    ftest_path = workspace / FTEST_DIR
    draft_path = ftest_path / DRAFT_DIR

    draft_path.mkdir(parents=True, exist_ok=True)

    for subdir in DRAFT_SUBDIRS:
        (draft_path / subdir).mkdir(exist_ok=True)

    config_path = draft_path / "ftest.yaml"
    config_path.write_text(
        yaml.dump(_default_config(workspace), default_flow_style=False),
        encoding="utf-8",
    )

    # Create / refresh .active — always defaults to draft on init
    set_active_version(workspace, DEFAULT_VERSION)

    return ftest_path
