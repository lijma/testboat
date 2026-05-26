"""ftest exec — run automation scripts and auto-record results."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ftest.commands.plan import get_run_command, list_plans
from ftest.commands.result import record_result


def run_case(
    ftest_root: Path,
    tc_id: str,
    by: str = "automation",
    _runner: callable = None,
) -> tuple[str, str]:
    """Run the automation script for *tc_id* and record the result.

    Returns (result_status, res_id).
    Raises FileNotFoundError if plan not found.
    Raises ValueError if plan has no automation configured.
    """
    tool, cmd = get_run_command(ftest_root, tc_id)
    if _runner is None:
        _runner = subprocess.run

    proc = _runner(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
    )
    status = "pass" if proc.returncode == 0 else "fail"
    notes = proc.stdout[-500:] if proc.stdout else proc.stderr[-500:]

    path = record_result(
        ftest_root,
        tc_id,
        status=status,
        execution_type="automated",
        by=by,
        notes=notes.strip(),
    )
    return status, path.stem


def run_sprint(
    ftest_root: Path,
    sprint: str | None = None,
    by: str = "automation",
    _runner: callable = None,
) -> dict[str, tuple[str, str]]:
    """Run all approved automated plans (optionally filtered by sprint tag).

    Returns {tc_id: (status, res_id)}.
    """
    plans = list_plans(ftest_root, execution_type=None, status="approved")
    results: dict[str, tuple[str, str]] = {}

    for plan in plans:
        if plan.get("execution_type") not in ("automated", "both"):
            continue
        if not plan.get("automation_tool"):
            continue
        tc_id = plan["tc_id"]
        try:
            status, res_id = run_case(ftest_root, tc_id, by=by, _runner=_runner)
            results[tc_id] = (status, res_id)
        except (FileNotFoundError, ValueError):
            results[tc_id] = ("blocked", "")

    return results
