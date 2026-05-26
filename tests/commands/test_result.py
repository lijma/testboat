"""Unit tests for testboat result / matrix / exec commands — 100% coverage."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from typer.testing import CliRunner

from testboat.cli import app
from testboat.commands.exec_ import run_case, run_sprint
from testboat.commands.plan import create_plan, set_plan_status
from testboat.commands.result import (
    ResultStatus,
    _matrix_path,
    _result_path,
    get_matrix,
    list_results,
    record_result,
    show_result,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_proc(returncode: int, stdout: str = "", stderr: str = "") -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


# ---------------------------------------------------------------------------
# record_result
# ---------------------------------------------------------------------------


class TestRecordResult:
    def test_creates_result_file(self, tmp_path: Path) -> None:
        record_result(tmp_path, "TC-001", "pass")
        assert _result_path(tmp_path, "RES-001").exists()

    def test_auto_increments_id(self, tmp_path: Path) -> None:
        record_result(tmp_path, "TC-001", "pass")
        record_result(tmp_path, "TC-001", "fail")
        assert _result_path(tmp_path, "RES-002").exists()

    def test_result_fields_stored(self, tmp_path: Path) -> None:
        record_result(tmp_path, "TC-001", "fail", by="tester", notes="broke")
        data = yaml.safe_load(_result_path(tmp_path, "RES-001").read_text())
        assert data["tc_id"] == "TC-001"
        assert data["status"] == "fail"
        assert data["executed_by"] == "tester"
        assert data["notes"] == "broke"

    def test_updates_matrix(self, tmp_path: Path) -> None:
        record_result(tmp_path, "TC-001", "pass")
        matrix = yaml.safe_load(_matrix_path(tmp_path).read_text())
        assert "TC-001" in matrix
        assert matrix["TC-001"]["latest_status"] == "pass"

    def test_matrix_tracks_multiple_results(self, tmp_path: Path) -> None:
        record_result(tmp_path, "TC-001", "fail")
        record_result(tmp_path, "TC-001", "pass")
        matrix = get_matrix(tmp_path)
        assert len(matrix["TC-001"]["result_ids"]) == 2
        assert matrix["TC-001"]["latest_status"] == "pass"

    def test_matrix_tracks_multiple_execution_types(self, tmp_path: Path) -> None:
        record_result(tmp_path, "TC-001", "pass", execution_type="manual")
        record_result(tmp_path, "TC-001", "pass", execution_type="automated")
        matrix = get_matrix(tmp_path)
        types = matrix["TC-001"]["execution_types_used"]
        assert "manual" in types
        assert "automated" in types

    def test_invalid_status_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Invalid status"):
            record_result(tmp_path, "TC-001", "flying")

    def test_returns_path(self, tmp_path: Path) -> None:
        path = record_result(tmp_path, "TC-001", "pass")
        assert path == _result_path(tmp_path, "RES-001")

    def test_duration_stored(self, tmp_path: Path) -> None:
        record_result(tmp_path, "TC-001", "pass", duration="2m30s")
        data = yaml.safe_load(_result_path(tmp_path, "RES-001").read_text())
        assert data["duration"] == "2m30s"


# ---------------------------------------------------------------------------
# list_results / show_result
# ---------------------------------------------------------------------------


class TestListResults:
    def test_returns_all_results(self, tmp_path: Path) -> None:
        record_result(tmp_path, "TC-001", "pass")
        record_result(tmp_path, "TC-002", "fail")
        assert len(list_results(tmp_path)) == 2

    def test_empty_when_none(self, tmp_path: Path) -> None:
        assert list_results(tmp_path) == []

    def test_filter_by_tc_id(self, tmp_path: Path) -> None:
        record_result(tmp_path, "TC-001", "pass")
        record_result(tmp_path, "TC-002", "fail")
        results = list_results(tmp_path, tc_id="TC-001")
        assert len(results) == 1
        assert results[0]["tc_id"] == "TC-001"


class TestShowResult:
    def test_returns_result(self, tmp_path: Path) -> None:
        record_result(tmp_path, "TC-001", "pass")
        data = show_result(tmp_path, "RES-001")
        assert data["id"] == "RES-001"

    def test_raises_if_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            show_result(tmp_path, "RES-999")


# ---------------------------------------------------------------------------
# get_matrix
# ---------------------------------------------------------------------------


class TestGetMatrix:
    def test_empty_when_no_results(self, tmp_path: Path) -> None:
        assert get_matrix(tmp_path) == {}

    def test_returns_all_entries(self, tmp_path: Path) -> None:
        record_result(tmp_path, "TC-001", "pass")
        record_result(tmp_path, "TC-002", "fail")
        matrix = get_matrix(tmp_path)
        assert "TC-001" in matrix
        assert "TC-002" in matrix

    def test_filter_by_tc_id(self, tmp_path: Path) -> None:
        record_result(tmp_path, "TC-001", "pass")
        record_result(tmp_path, "TC-002", "fail")
        matrix = get_matrix(tmp_path, tc_id="TC-001")
        assert list(matrix.keys()) == ["TC-001"]

    def test_missing_tc_returns_empty(self, tmp_path: Path) -> None:
        record_result(tmp_path, "TC-001", "pass")
        assert get_matrix(tmp_path, tc_id="TC-999") == {}


# ---------------------------------------------------------------------------
# exec_.run_case
# ---------------------------------------------------------------------------


class TestRunCase:
    def test_pass_on_zero_returncode(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", execution_type="automated")
        set_plan_status(tmp_path, "TC-001", "approved")
        mock_runner = MagicMock(return_value=_make_proc(0, stdout="all good"))
        status, res_id = run_case(tmp_path, "TC-001", _runner=mock_runner)
        assert status == "pass"
        assert res_id.startswith("RES-")

    def test_fail_on_nonzero_returncode(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", execution_type="automated")
        mock_runner = MagicMock(return_value=_make_proc(1, stderr="error"))
        status, _ = run_case(tmp_path, "TC-001", _runner=mock_runner)
        assert status == "fail"

    def test_records_result_automatically(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", execution_type="automated")
        mock_runner = MagicMock(return_value=_make_proc(0))
        run_case(tmp_path, "TC-001", _runner=mock_runner)
        assert len(list_results(tmp_path, tc_id="TC-001")) == 1

    def test_raises_if_no_automation(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", execution_type="manual")
        with pytest.raises(ValueError):
            run_case(tmp_path, "TC-001")

    def test_raises_if_plan_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            run_case(tmp_path, "TC-999")

    def test_uses_stderr_when_stdout_empty(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", execution_type="automated")
        mock_runner = MagicMock(return_value=_make_proc(1, stdout="", stderr="err msg"))
        run_case(tmp_path, "TC-001", _runner=mock_runner)
        result = list_results(tmp_path, tc_id="TC-001")[0]
        assert "err msg" in result["notes"]


# ---------------------------------------------------------------------------
# exec_.run_sprint
# ---------------------------------------------------------------------------


class TestRunSprint:
    def test_runs_approved_automated_plans(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", execution_type="automated")
        set_plan_status(tmp_path, "TC-001", "approved")
        mock_runner = MagicMock(return_value=_make_proc(0))
        results = run_sprint(tmp_path, _runner=mock_runner)
        assert "TC-001" in results

    def test_skips_unapproved_plans(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", execution_type="automated")
        # plan remains draft
        mock_runner = MagicMock(return_value=_make_proc(0))
        results = run_sprint(tmp_path, _runner=mock_runner)
        assert results == {}

    def test_skips_manual_plans(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", execution_type="manual")
        set_plan_status(tmp_path, "TC-001", "approved")
        mock_runner = MagicMock(return_value=_make_proc(0))
        results = run_sprint(tmp_path, _runner=mock_runner)
        assert results == {}

    def test_blocked_when_run_case_raises(self, tmp_path: Path) -> None:
        # Create an approved automated plan but with automation_path=null → run_case raises ValueError
        from testboat.commands.plan import _plan_path
        _plan_path(tmp_path, "TC-001").parent.mkdir(parents=True, exist_ok=True)
        _plan_path(tmp_path, "TC-001").write_text(
            "tc_id: TC-001\nstatus: approved\nexecution_type: automated\n"
            "automation_tool: playwright\nautomation_path: null\n"
            "notes: ''\ncreated_at: '2026-01-01'\nexecutor: null\n"
        )
        mock_runner = MagicMock(return_value=_make_proc(0))
        results = run_sprint(tmp_path, _runner=mock_runner)
        assert results["TC-001"][0] == "blocked"

    def test_empty_when_no_plans(self, tmp_path: Path) -> None:
        mock_runner = MagicMock(return_value=_make_proc(0))
        assert run_sprint(tmp_path, _runner=mock_runner) == {}

    def test_skips_plan_without_tool(self, tmp_path: Path) -> None:
        # Approved automated plan with null automation_tool → skipped silently
        from testboat.commands.plan import _plan_path
        _plan_path(tmp_path, "TC-001").parent.mkdir(parents=True, exist_ok=True)
        _plan_path(tmp_path, "TC-001").write_text(
            "tc_id: TC-001\nstatus: approved\nexecution_type: automated\n"
            "automation_tool: null\nautomation_path: null\n"
            "notes: ''\ncreated_at: '2026-01-01'\nexecutor: null\n"
        )
        mock_runner = MagicMock(return_value=_make_proc(0))
        results = run_sprint(tmp_path, _runner=mock_runner)
        assert "TC-001" not in results


# ---------------------------------------------------------------------------
# CLI: result
# ---------------------------------------------------------------------------


class TestResultCli:
    def test_record_exits_zero(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["result", "record", "TC-001", "pass",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "RES-001" in result.output

    def test_record_invalid_status_exits_one(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["result", "record", "TC-001", "flying",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_list_empty(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["result", "list", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "No results" in result.output

    def test_list_shows_results(self, tmp_path: Path) -> None:
        record_result(tmp_path, "TC-001", "pass")
        result = runner.invoke(app, ["result", "list", "--workspace", str(tmp_path)])
        assert "RES-001" in result.output

    def test_show_result(self, tmp_path: Path) -> None:
        record_result(tmp_path, "TC-001", "pass")
        result = runner.invoke(app, ["result", "show", "RES-001", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "tc_id" in result.output

    def test_show_not_found(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["result", "show", "RES-999", "--workspace", str(tmp_path)])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# CLI: matrix
# ---------------------------------------------------------------------------


class TestMatrixCli:
    def test_show_empty(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["matrix", "show", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "No execution data" in result.output

    def test_show_with_data(self, tmp_path: Path) -> None:
        record_result(tmp_path, "TC-001", "pass")
        result = runner.invoke(app, ["matrix", "show", "--workspace", str(tmp_path)])
        assert "TC-001" in result.output
        assert "pass" in result.output

    def test_show_filter_by_tc(self, tmp_path: Path) -> None:
        record_result(tmp_path, "TC-001", "pass")
        record_result(tmp_path, "TC-002", "fail")
        result = runner.invoke(app, ["matrix", "show", "TC-001", "--workspace", str(tmp_path)])
        assert "TC-001" in result.output
        assert "TC-002" not in result.output


# ---------------------------------------------------------------------------
# CLI: exec
# ---------------------------------------------------------------------------


class TestExecRunCase:
    """Tests for exec_.run_case — not via CLI (testboat exec removed)."""

    def test_exec_single_pass(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", execution_type="automated")
        mock = MagicMock(return_value=_make_proc(0))
        status, _ = run_case(tmp_path, "TC-001", _runner=mock)
        assert status == "pass"

    def test_exec_single_fail(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", execution_type="automated")
        mock = MagicMock(return_value=_make_proc(1))
        status, _ = run_case(tmp_path, "TC-001", _runner=mock)
        assert status == "fail"

    def test_exec_batch_pass(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", execution_type="automated")
        set_plan_status(tmp_path, "TC-001", "approved")
        mock = MagicMock(return_value=_make_proc(0))
        results = run_sprint(tmp_path, _runner=mock)
        assert results["TC-001"][0] == "pass"

    def test_exec_batch_fail(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", execution_type="automated")
        set_plan_status(tmp_path, "TC-001", "approved")
        mock = MagicMock(return_value=_make_proc(1))
        results = run_sprint(tmp_path, _runner=mock)
        assert results["TC-001"][0] == "fail"

    def test_run_case_resolves_subprocess_when_runner_none(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", execution_type="automated")
        with patch("testboat.commands.exec_.subprocess.run", return_value=_make_proc(0, stdout="ok")):
            status, _ = run_case(tmp_path, "TC-001")  # _runner=None → uses subprocess.run
        assert status == "pass"
