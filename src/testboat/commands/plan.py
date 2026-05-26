"""testboat plan — execution plan per test case."""

from __future__ import annotations
from testboat.commands.active import active_dir

from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

PLANS_DIR = "executions/plans"

# Default automation tool per TC type
TOOL_DEFAULTS: dict[str, str] = {
    "functional": "playwright",
    "regression": "playwright",
    "smoke": "playwright",
    "performance": "jmeter",
    "security": "zap",
    "accessibility": "playwright",
    "exploratory": "manual",
}

# How each tool runs its script
TOOL_RUN_COMMANDS: dict[str, str] = {
    "playwright": "npx playwright test {path}",
    "maestro":    "maestro test {path}",
    "jmeter":     "jmeter -n -t {path} -l /tmp/jmeter-result.jtl",
    "pytest":     "python -m pytest {path} -v",
    "bash":       "bash {path}",
    "zap":        "zap-cli quick-scan --self-contained --start-options '-config api.disablekey=true' {path}",
    "nuclei":     "nuclei -t {path}",
}


class ExecutionType(str, Enum):
    manual = "manual"
    automated = "automated"
    both = "both"


class AutomationTool(str, Enum):
    playwright = "playwright"
    maestro = "maestro"
    jmeter = "jmeter"
    zap = "zap"
    nuclei = "nuclei"
    pytest = "pytest"
    bash = "bash"


class PlanStatus(str, Enum):
    draft = "draft"
    approved = "approved"


class Plan(BaseModel):
    tc_id: str
    status: PlanStatus
    execution_type: ExecutionType
    automation_tool: AutomationTool | None = None
    automation_path: str | None = None
    executor: str | None = None
    notes: str = ""
    created_at: str


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def _plans_dir(testboat_root: Path) -> Path:
    return active_dir(testboat_root) / PLANS_DIR


def _plan_path(testboat_root: Path, tc_id: str) -> Path:
    return _plans_dir(testboat_root) / f"{tc_id}-plan.yaml"


def _automate_root(testboat_root: Path) -> Path:
    return active_dir(testboat_root) / "executions" / "automate"


def _automate_path(testboat_root: Path, tc_id: str) -> Path:
    return _automate_root(testboat_root) / tc_id


def _load_plan(testboat_root: Path, tc_id: str) -> dict[str, Any]:
    path = _plan_path(testboat_root, tc_id)
    if not path.exists():
        raise FileNotFoundError(f"Plan for {tc_id} not found. Run `testboat plan create {tc_id}` first.")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _save_plan(testboat_root: Path, data: dict[str, Any]) -> Path:
    path = _plan_path(testboat_root, data["tc_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

def create_plan(
    testboat_root: Path,
    tc_id: str,
    execution_type: str = "manual",
    tool: str | None = None,
    executor: str | None = None,
    notes: str = "",
) -> Path:
    """Create or overwrite execution plan for *tc_id*. Idempotent.

    Raises ValueError for invalid execution_type or tool.
    """
    try:
        et = ExecutionType(execution_type)
    except ValueError:
        valid = ", ".join(e.value for e in ExecutionType)
        raise ValueError(f"Invalid execution_type '{execution_type}'. Valid: {valid}")

    resolved_tool: str | None = None
    if et in (ExecutionType.automated, ExecutionType.both):
        if tool:
            try:
                AutomationTool(tool)
                resolved_tool = tool
            except ValueError:
                valid = ", ".join(e.value for e in AutomationTool)
                raise ValueError(f"Invalid tool '{tool}'. Valid: {valid}")
        else:
            resolved_tool = "playwright"  # default

    automation_path: str | None = None
    if resolved_tool:
        automate_dir = _automate_path(testboat_root, tc_id)
        automation_path = str(automate_dir.relative_to(testboat_root))

    data: dict[str, Any] = {
        "tc_id": tc_id,
        "status": PlanStatus.draft.value,
        "execution_type": et.value,
        "automation_tool": resolved_tool,
        "automation_path": automation_path,
        "executor": executor,
        "notes": notes,
        "created_at": str(date.today()),
    }
    return _save_plan(testboat_root, data)


def list_plans(
    testboat_root: Path,
    execution_type: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Return list of plan dicts, optionally filtered."""
    plans_dir = _plans_dir(testboat_root)
    if not plans_dir.exists():
        return []
    results = []
    for path in sorted(plans_dir.glob("TC-*-plan.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if execution_type and data.get("execution_type") != execution_type:
            continue
        if status and data.get("status") != status:
            continue
        results.append(data)
    return results


def show_plan(testboat_root: Path, tc_id: str) -> dict[str, Any]:
    """Return plan data. Raises FileNotFoundError if not found."""
    return _load_plan(testboat_root, tc_id)


def set_plan_status(testboat_root: Path, tc_id: str, new_status: str) -> None:
    """Update plan status. Raises ValueError for unknown status."""
    try:
        PlanStatus(new_status)
    except ValueError:
        valid = ", ".join(s.value for s in PlanStatus)
        raise ValueError(f"Invalid status '{new_status}'. Valid: {valid}")
    data = _load_plan(testboat_root, tc_id)
    data["status"] = new_status
    _save_plan(testboat_root, data)


def register_automation(
    testboat_root: Path,
    tc_id: str,
    script_path: str,
    tool: str | None = None,
) -> Path:
    """Register an automation script to tc_id's plan.

    *script_path* is relative to testboat_root (e.g. .testboat/draft/executions/automate/pytest/tests/test_TC001.py).
    *tool* is inferred from file extension if not provided.
    Raises FileNotFoundError if plan not found.
    Raises ValueError for unknown tool.
    """
    data = _load_plan(testboat_root, tc_id)

    resolved_tool = tool
    if not resolved_tool:
        ext = Path(script_path).suffix.lower()
        resolved_tool = {
            ".ts": "playwright", ".js": "playwright",
            ".py": "pytest",
            ".jmx": "jmeter",
            ".yaml": "maestro", ".yml": "maestro",
            ".sh": "bash",
        }.get(ext, "bash")

    try:
        AutomationTool(resolved_tool)
    except ValueError:
        valid = ", ".join(e.value for e in AutomationTool)
        raise ValueError(f"Invalid tool '{resolved_tool}'. Valid: {valid}")

    data["automation_tool"] = resolved_tool
    data["automation_path"] = script_path
    if data.get("execution_type") == ExecutionType.manual.value:
        data["execution_type"] = ExecutionType.automated.value
    return _save_plan(testboat_root, data)


def get_run_command(testboat_root: Path, tc_id: str) -> tuple[str, str]:
    """Return (tool, shell_command) for running the automation script.

    Raises FileNotFoundError if plan not found.
    Raises ValueError if plan has no automation.
    """
    data = _load_plan(testboat_root, tc_id)
    tool = data.get("automation_tool")
    path = data.get("automation_path")
    if not tool or not path:
        raise ValueError(f"{tc_id} plan has no automation configured.")
    cmd_template = TOOL_RUN_COMMANDS.get(tool, "{path}")
    return tool, cmd_template.format(path=str(testboat_root / path))
