"""testboat bug — bug / defect lifecycle management."""

from __future__ import annotations
from testboat.commands.active import active_dir

from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_validator

BUGS_DIR = "bugs"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    critical = "critical"
    major = "major"
    minor = "minor"
    cosmetic = "cosmetic"


class BugPriority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class BugStatus(str, Enum):
    new = "new"
    triaged = "triaged"
    in_progress = "in-progress"
    fixed = "fixed"
    pending_retest = "pending-retest"
    verified = "verified"
    closed = "closed"
    deferred = "deferred"
    wont_fix = "wont-fix"


class BugTags(BaseModel):
    sprint: str | None = None
    type: str | None = None
    module: str | None = None


class BugModel(BaseModel):
    id: str
    title: str
    status: BugStatus
    severity: Severity
    priority: BugPriority
    tags: BugTags = BugTags()
    tc_id: str = ""
    result_id: str = ""
    environment: str = ""
    steps_to_reproduce: list[str] = []
    expected: str = ""
    actual: str = ""
    reporter: str = ""
    assignee: str = ""
    found_at: str = ""
    fixed_at: str | None = None
    notes: str = ""

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title must not be empty")
        return v


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

_VALID_TRANSITIONS: dict[BugStatus, set[BugStatus]] = {
    BugStatus.new:           {BugStatus.triaged},
    BugStatus.triaged:       {BugStatus.in_progress, BugStatus.deferred, BugStatus.wont_fix},
    BugStatus.in_progress:   {BugStatus.fixed, BugStatus.deferred, BugStatus.wont_fix},
    BugStatus.fixed:         {BugStatus.pending_retest},
    BugStatus.pending_retest:{BugStatus.verified, BugStatus.in_progress},
    BugStatus.verified:      {BugStatus.closed},
    BugStatus.deferred:      {BugStatus.triaged},
    BugStatus.closed:        set(),
    BugStatus.wont_fix:      set(),
}


def _valid_transition(current: BugStatus, target: BugStatus) -> bool:
    return target in _VALID_TRANSITIONS.get(current, set())


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def _bugs_dir(testboat_root: Path) -> Path:
    return active_dir(testboat_root) /  BUGS_DIR


def _bug_path(testboat_root: Path, bug_id: str) -> Path:
    return _bugs_dir(testboat_root) / f"{bug_id}.yaml"


def _next_id(testboat_root: Path) -> str:
    existing = sorted(_bugs_dir(testboat_root).glob("BUG-*.yaml"))
    if not existing:
        return "BUG-001"
    seq = int(existing[-1].stem.split("-")[1]) + 1
    return f"BUG-{seq:03d}"


def _load_bug(testboat_root: Path, bug_id: str) -> dict[str, Any]:
    path = _bug_path(testboat_root, bug_id)
    if not path.exists():
        raise FileNotFoundError(f"{bug_id} not found in bugs/")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _save_bug(testboat_root: Path, data: dict[str, Any]) -> Path:
    path = _bug_path(testboat_root, data["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

def add_bug(
    testboat_root: Path,
    title: str,
    severity: str = "major",
    priority: str = "P2",
    tc_id: str = "",
    result_id: str = "",
    environment: str = "",
    notes: str = "",
    sprint: str | None = None,
    type_: str | None = None,
    module: str | None = None,
) -> Path:
    """Create a new BUG-xxx.yaml. Returns the created file path.

    Raises ValueError for invalid severity or priority.
    """
    try:
        Severity(severity)
    except ValueError:
        valid = ", ".join(s.value for s in Severity)
        raise ValueError(f"Invalid severity '{severity}'. Valid: {valid}")
    try:
        BugPriority(priority)
    except ValueError:
        valid = ", ".join(s.value for s in BugPriority)
        raise ValueError(f"Invalid priority '{priority}'. Valid: {valid}")

    bug_id = _next_id(testboat_root)
    data: dict[str, Any] = {
        "id": bug_id,
        "title": title,
        "status": BugStatus.new.value,
        "severity": severity,
        "priority": priority,
        "tags": {
            "sprint": sprint,
            "type": type_,
            "module": module,
        },
        "tc_id": tc_id,
        "result_id": result_id,
        "environment": environment,
        "steps_to_reproduce": [],
        "expected": "",
        "actual": "",
        "reporter": "",
        "assignee": "",
        "found_at": str(date.today()),
        "fixed_at": None,
        "notes": notes,
    }
    return _save_bug(testboat_root, data)


def list_bugs(
    testboat_root: Path,
    status: str | None = None,
    severity: str | None = None,
    priority: str | None = None,
    sprint: str | None = None,
    type_: str | None = None,
    module: str | None = None,
) -> list[dict[str, Any]]:
    """Return bugs, optionally filtered."""
    bugs_dir = _bugs_dir(testboat_root)
    if not bugs_dir.exists():
        return []
    results = []
    for path in sorted(bugs_dir.glob("BUG-*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if status and data.get("status") != status:
            continue
        if severity and data.get("severity") != severity:
            continue
        if priority and data.get("priority") != priority:
            continue
        tags = data.get("tags") or {}
        if sprint and tags.get("sprint") != sprint:
            continue
        if type_ and tags.get("type") != type_:
            continue
        if module and tags.get("module") != module:
            continue
        results.append(data)
    return results


def show_bug(testboat_root: Path, bug_id: str) -> dict[str, Any]:
    """Return bug data. Raises FileNotFoundError if not found."""
    return _load_bug(testboat_root, bug_id)


def set_bug_status(testboat_root: Path, bug_id: str, new_status: str) -> None:
    """Transition bug to new_status.

    Raises ValueError for invalid status or illegal transition.
    Raises FileNotFoundError if bug not found.
    """
    try:
        target = BugStatus(new_status)
    except ValueError:
        valid = ", ".join(s.value for s in BugStatus)
        raise ValueError(f"Invalid status '{new_status}'. Valid: {valid}")

    data = _load_bug(testboat_root, bug_id)
    current = BugStatus(data["status"])

    if not _valid_transition(current, target):
        raise ValueError(
            f"Cannot transition {bug_id} from '{current.value}' to '{target.value}'"
        )

    data["status"] = target.value
    if target == BugStatus.fixed:
        data["fixed_at"] = str(date.today())
    _save_bug(testboat_root, data)
