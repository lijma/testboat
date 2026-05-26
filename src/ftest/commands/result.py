"""ftest result — execution results + global execution matrix."""

from __future__ import annotations
from ftest.commands.active import active_dir

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

RESULTS_DIR = "executions/results"
MATRIX_FILE = "executions/execution-matrix.yaml"


class ResultStatus(str, Enum):
    pass_ = "pass"
    fail = "fail"
    blocked = "blocked"
    skipped = "skipped"


class ResultModel(BaseModel):
    id: str
    tc_id: str
    execution_type: str
    status: ResultStatus
    executed_at: str
    executed_by: str = ""
    duration: str = ""
    notes: str = ""


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def _results_dir(ftest_root: Path) -> Path:
    return active_dir(ftest_root) / RESULTS_DIR


def _result_path(ftest_root: Path, res_id: str) -> Path:
    return _results_dir(ftest_root) / f"{res_id}.yaml"


def _matrix_path(ftest_root: Path) -> Path:
    return active_dir(ftest_root) / MATRIX_FILE


def _next_result_id(ftest_root: Path) -> str:
    existing = sorted(_results_dir(ftest_root).glob("RES-*.yaml"))
    if not existing:
        return "RES-001"
    seq = int(existing[-1].stem.split("-")[1]) + 1
    return f"RES-{seq:03d}"


def _load_matrix(ftest_root: Path) -> dict[str, Any]:
    path = _matrix_path(ftest_root)
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _save_matrix(ftest_root: Path, data: dict[str, Any]) -> None:
    path = _matrix_path(ftest_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True), encoding="utf-8")


def _update_matrix(ftest_root: Path, tc_id: str, res_id: str,
                   status: str, execution_type: str, executed_at: str) -> None:
    matrix = _load_matrix(ftest_root)
    entry = matrix.get(tc_id, {
        "latest_status": status,
        "execution_types_used": [],
        "result_ids": [],
        "last_executed": executed_at,
    })
    entry["latest_status"] = status
    entry["last_executed"] = executed_at
    if res_id not in entry["result_ids"]:
        entry["result_ids"].append(res_id)
    if execution_type not in entry["execution_types_used"]:
        entry["execution_types_used"].append(execution_type)
    matrix[tc_id] = entry
    _save_matrix(ftest_root, matrix)


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

def record_result(
    ftest_root: Path,
    tc_id: str,
    status: str,
    execution_type: str = "manual",
    by: str = "",
    duration: str = "",
    notes: str = "",
) -> Path:
    """Record one execution result and update the execution matrix.

    Raises ValueError for invalid status.
    Returns the created result file path.
    """
    try:
        ResultStatus(status)
    except ValueError:
        valid = ", ".join(s.value for s in ResultStatus)
        raise ValueError(f"Invalid status '{status}'. Valid: {valid}")

    _results_dir(ftest_root).mkdir(parents=True, exist_ok=True)
    res_id = _next_result_id(ftest_root)
    now = datetime.now().isoformat(timespec="seconds")

    data: dict[str, Any] = {
        "id": res_id,
        "tc_id": tc_id,
        "execution_type": execution_type,
        "status": status,
        "executed_at": now,
        "executed_by": by,
        "duration": duration,
        "notes": notes,
    }
    path = _result_path(ftest_root, res_id)
    path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True), encoding="utf-8")

    _update_matrix(ftest_root, tc_id, res_id, status, execution_type, now)
    return path


def list_results(ftest_root: Path, tc_id: str | None = None) -> list[dict[str, Any]]:
    """Return list of results, optionally filtered by tc_id."""
    results_dir = _results_dir(ftest_root)
    if not results_dir.exists():
        return []
    results = []
    for path in sorted(results_dir.glob("RES-*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if tc_id and data.get("tc_id") != tc_id:
            continue
        results.append(data)
    return results


def show_result(ftest_root: Path, res_id: str) -> dict[str, Any]:
    """Return result data. Raises FileNotFoundError if not found."""
    path = _result_path(ftest_root, res_id)
    if not path.exists():
        raise FileNotFoundError(f"{res_id} not found.")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def get_matrix(ftest_root: Path, tc_id: str | None = None) -> dict[str, Any]:
    """Return execution matrix, optionally filtered to one TC."""
    matrix = _load_matrix(ftest_root)
    if tc_id:
        return {tc_id: matrix[tc_id]} if tc_id in matrix else {}
    return matrix
