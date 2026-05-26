"""testboat case — test case CRUD + state machine."""

from __future__ import annotations
from testboat.commands.active import active_dir

from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_validator

from testboat.commands.tag import tag_exists

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

CASES_DIR = "cases"


class CaseStatus(str, Enum):
    draft = "draft"
    ready = "ready"
    pass_ = "pass"
    fail = "fail"
    blocked = "blocked"
    skipped = "skipped"


class Priority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class Automation(str, Enum):
    manual = "manual"
    automated = "automated"
    to_automate = "to-automate"


class Step(BaseModel):
    action: str
    expected: str


class Tags(BaseModel):
    sprint: str | None = None
    type: str | None = None
    module: str | None = None


class CaseModel(BaseModel):
    id: str
    title: str
    status: CaseStatus
    priority: Priority
    automation: Automation
    tags: Tags
    preconditions: list[str] = []
    steps: list[Step] = []
    expected_result: str = ""
    req_id: str = ""
    notes: str = ""

    @field_validator("steps")
    @classmethod
    def steps_required_when_ready(cls, v: list[Step]) -> list[Step]:
        return v


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

_VALID_TRANSITIONS: dict[CaseStatus, set[CaseStatus]] = {
    CaseStatus.draft:    {CaseStatus.ready},
    CaseStatus.ready:    {CaseStatus.pass_, CaseStatus.fail,
                          CaseStatus.blocked, CaseStatus.skipped, CaseStatus.draft},
    CaseStatus.pass_:    {CaseStatus.ready},
    CaseStatus.fail:     {CaseStatus.ready},
    CaseStatus.blocked:  {CaseStatus.ready},
    CaseStatus.skipped:  {CaseStatus.ready},
}


def _valid_transition(current: CaseStatus, target: CaseStatus) -> bool:
    return target in _VALID_TRANSITIONS.get(current, set())


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def _cases_dir(testboat_root: Path) -> Path:
    return active_dir(testboat_root) /  CASES_DIR


def _case_path(testboat_root: Path, tc_id: str) -> Path:
    return _cases_dir(testboat_root) / f"{tc_id}.yaml"


def _next_id(testboat_root: Path) -> str:
    existing = sorted(_cases_dir(testboat_root).glob("TC-*.yaml"))
    if not existing:
        return "TC-001"
    last = existing[-1].stem  # e.g. "TC-007"
    seq = int(last.split("-")[1]) + 1
    return f"TC-{seq:03d}"


def _load_case(testboat_root: Path, tc_id: str) -> dict[str, Any]:
    path = _case_path(testboat_root, tc_id)
    if not path.exists():
        raise FileNotFoundError(f"{tc_id} not found in cases/")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _save_case(testboat_root: Path, data: dict[str, Any]) -> Path:
    path = _case_path(testboat_root, data["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

def add_case(
    testboat_root: Path,
    title: str,
    priority: str = "P2",
    sprint: str | None = None,
    type_: str | None = None,
    module: str | None = None,
    req_id: str = "",
) -> Path:
    """Create a new TC-xxx.yaml with metadata only (steps left empty for AI).

    Returns the created file path.
    Raises ValueError if a referenced tag does not exist.
    """
    for kind, value in [("sprint", sprint), ("type", type_), ("module", module)]:
        if value and not tag_exists(testboat_root, kind, value):
            raise ValueError(
                f"Tag {kind}='{value}' does not exist. "
                f"Run `testboat tag add {kind} {value}` first."
            )

    tc_id = _next_id(testboat_root)
    data: dict[str, Any] = {
        "id": tc_id,
        "title": title,
        "status": CaseStatus.draft.value,
        "priority": priority,
        "automation": Automation.to_automate.value,
        "tags": {
            "sprint": sprint,
            "type": type_,
            "module": module,
        },
        "req_id": req_id,
        "preconditions": [],
        "steps": [],
        "expected_result": "",
        "notes": "",
    }
    return _save_case(testboat_root, data)


def list_cases(
    testboat_root: Path,
    sprint: str | None = None,
    type_: str | None = None,
    module: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Return list of case dicts, optionally filtered."""
    cases_dir = _cases_dir(testboat_root)
    if not cases_dir.exists():
        return []
    results = []
    for path in sorted(cases_dir.glob("TC-*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        tags = data.get("tags") or {}
        if sprint and tags.get("sprint") != sprint:
            continue
        if type_ and tags.get("type") != type_:
            continue
        if module and tags.get("module") != module:
            continue
        if status and data.get("status") != status:
            continue
        results.append(data)
    return results


def show_case(testboat_root: Path, tc_id: str) -> dict[str, Any]:
    """Return case data. Raises FileNotFoundError if not found."""
    return _load_case(testboat_root, tc_id)


def set_status(testboat_root: Path, tc_id: str, new_status: str) -> None:
    """Transition tc_id to new_status.

    Raises ValueError for invalid transitions.
    Raises FileNotFoundError if tc_id not found.
    """
    data = _load_case(testboat_root, tc_id)
    current = CaseStatus(data["status"])
    try:
        target = CaseStatus(new_status)
    except ValueError:
        valid = [s.value for s in CaseStatus]
        raise ValueError(f"Unknown status '{new_status}'. Valid: {', '.join(valid)}")

    if not _valid_transition(current, target):
        raise ValueError(
            f"Cannot transition {tc_id} from '{current.value}' to '{target.value}'"
        )
    data["status"] = target.value
    _save_case(testboat_root, data)


def validate_cases_batch(
    testboat_root: Path,
    sprint: str | None = None,
    type_: str | None = None,
    module: str | None = None,
    status: str | None = None,
) -> dict[str, list[str]]:
    """Validate all cases matching the given filters.

    Returns {tc_id: [errors]} for every matched case.
    Empty error list means the case is valid.
    """
    cases = list_cases(testboat_root, sprint=sprint, type_=type_,
                       module=module, status=status)
    return {c["id"]: validate_case(testboat_root, c["id"]) for c in cases}


def validate_case(testboat_root: Path, tc_id: str) -> list[str]:
    """Validate TC schema + tag references.

    Returns list of error strings (empty = valid).
    Raises FileNotFoundError if tc_id not found.
    """
    data = _load_case(testboat_root, tc_id)
    errors: list[str] = []

    # Pydantic schema check
    from pydantic import ValidationError
    try:
        CaseModel.model_validate(data)
    except ValidationError as exc:
        errors.extend(f"{e['loc']}: {e['msg']}" for e in exc.errors())

    # Tag reference check
    tags = data.get("tags") or {}
    for kind in ("sprint", "type", "module"):
        value = tags.get(kind)
        if value and not tag_exists(testboat_root, kind, value):
            errors.append(f"tags.{kind}: '{value}' not found in tags registry")

    # Steps required when status != draft
    status = data.get("status", "draft")
    steps = data.get("steps") or []
    if status != CaseStatus.draft.value and not steps:
        errors.append(f"steps: required when status is '{status}'")

    return errors
