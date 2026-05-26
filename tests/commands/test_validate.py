"""Unit tests for testboat validate command — 100% coverage."""

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from testboat.cli import app
from testboat.commands.bug import add_bug, set_bug_status
from testboat.commands.case import add_case, set_status
from testboat.commands.plan import create_plan, register_automation, set_plan_status
from testboat.commands.result import record_result
from testboat.commands.strategy import create_strategy
from testboat.commands.tag import add_tag
from testboat.commands.validate import (
    ValidateReport,
    _check_execution_completeness,
    _check_exit_criteria,
    _check_format,
    _check_requirements_coverage,
    run_validate,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_full_workspace(root: Path) -> None:
    """Create a minimal passing workspace."""
    add_tag(root, "sprint", "v1.0.0")
    add_tag(root, "type", "functional")
    add_tag(root, "module", "auth")
    create_strategy(root)
    add_case(root, "Login test", sprint="v1.0.0", type_="functional",
             module="auth", req_id="STORY-001")
    # add steps so validate passes when status != draft
    tc_path = root / ".testboat" / "draft" / "cases" / "TC-001.yaml"
    data = yaml.safe_load(tc_path.read_text())
    data["steps"] = [{"action": "do thing", "expected": "result"}]
    data["expected_result"] = "all good"
    tc_path.write_text(yaml.dump(data, allow_unicode=True))
    set_status(root, "TC-001", "ready")
    record_result(root, "TC-001", "pass", execution_type="automated")
    set_status(root, "TC-001", "pass")


def _write_strategy(root: Path, data: dict) -> None:
    path = root / ".testboat" / "draft" / "strategy.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")


# ---------------------------------------------------------------------------
# Check 1: Format validation
# ---------------------------------------------------------------------------


class TestCheckFormat:
    def test_passes_on_valid_workspace(self, tmp_path: Path) -> None:
        add_tag(tmp_path, "sprint", "v1.0.0")
        create_strategy(tmp_path)
        add_case(tmp_path, "Test", sprint="v1.0.0")
        result = _check_format(tmp_path)
        assert result.passed

    def test_fails_when_no_strategy(self, tmp_path: Path) -> None:
        add_case(tmp_path, "Test")
        result = _check_format(tmp_path)
        assert not result.passed
        assert any("strategy.yaml" in d for d in result.details)

    def test_fails_when_strategy_invalid(self, tmp_path: Path) -> None:
        from testboat.commands.strategy import STRATEGY_FILE
        path = tmp_path / ".testboat" / "draft" / STRATEGY_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("status: garbage\nrelease: v1\n")
        add_case(tmp_path, "Test")
        result = _check_format(tmp_path)
        assert not result.passed

    def test_fails_when_no_cases(self, tmp_path: Path) -> None:
        create_strategy(tmp_path)
        result = _check_format(tmp_path)
        assert not result.passed
        assert any("no test cases" in d for d in result.details)

    def test_fails_when_case_invalid(self, tmp_path: Path) -> None:
        add_tag(tmp_path, "sprint", "v1.0.0")
        create_strategy(tmp_path)
        add_case(tmp_path, "Test", sprint="v1.0.0")
        tc_path = tmp_path / ".testboat" / "draft" / "cases" / "TC-001.yaml"
        data = yaml.safe_load(tc_path.read_text())
        data["tags"]["sprint"] = "nonexistent"
        tc_path.write_text(yaml.dump(data))
        result = _check_format(tmp_path)
        assert not result.passed


# ---------------------------------------------------------------------------
# Check 2: Requirements coverage
# ---------------------------------------------------------------------------


class TestCheckRequirementsCoverage:
    def test_passes_when_all_have_req_id(self, tmp_path: Path) -> None:
        add_case(tmp_path, "Test", req_id="STORY-001")
        result = _check_requirements_coverage(tmp_path)
        assert result.passed
        assert any("STORY-001" in d for d in result.details)

    def test_fails_when_tc_has_no_req_id(self, tmp_path: Path) -> None:
        add_case(tmp_path, "Test")  # no req_id
        result = _check_requirements_coverage(tmp_path)
        assert not result.passed
        assert any("TC-001" in d for d in result.details)

    def test_fails_when_no_cases(self, tmp_path: Path) -> None:
        result = _check_requirements_coverage(tmp_path)
        assert not result.passed

    def test_multiple_tcs_same_req(self, tmp_path: Path) -> None:
        add_case(tmp_path, "Test A", req_id="STORY-001")
        add_case(tmp_path, "Test B", req_id="STORY-001")
        result = _check_requirements_coverage(tmp_path)
        assert result.passed
        assert any("TC-001" in d and "TC-002" in d for d in result.details)


# ---------------------------------------------------------------------------
# Check 3: Execution completeness
# ---------------------------------------------------------------------------


class TestCheckExecutionCompleteness:
    def test_passes_when_all_executed(self, tmp_path: Path) -> None:
        add_case(tmp_path, "Test")
        set_status(tmp_path, "TC-001", "ready")
        record_result(tmp_path, "TC-001", "pass")
        result = _check_execution_completeness(tmp_path)
        assert result.passed

    def test_fails_when_tc_not_executed(self, tmp_path: Path) -> None:
        add_case(tmp_path, "Test")
        set_status(tmp_path, "TC-001", "ready")
        # no result recorded
        result = _check_execution_completeness(tmp_path)
        assert not result.passed
        assert any("TC-001" in d for d in result.details)

    def test_fails_when_no_non_draft_cases(self, tmp_path: Path) -> None:
        add_case(tmp_path, "Test")  # stays draft
        result = _check_execution_completeness(tmp_path)
        assert not result.passed

    def test_shows_pass_fail_summary(self, tmp_path: Path) -> None:
        add_case(tmp_path, "Test")
        set_status(tmp_path, "TC-001", "ready")
        record_result(tmp_path, "TC-001", "pass")
        result = _check_execution_completeness(tmp_path)
        assert any("pass" in d for d in result.details)

    def test_draft_cases_excluded(self, tmp_path: Path) -> None:
        add_case(tmp_path, "Draft TC")  # draft only
        add_case(tmp_path, "Ready TC")
        set_status(tmp_path, "TC-002", "ready")
        record_result(tmp_path, "TC-002", "pass")
        result = _check_execution_completeness(tmp_path)
        assert result.passed  # TC-001 is draft, excluded


# ---------------------------------------------------------------------------
# Check 4: Exit criteria
# ---------------------------------------------------------------------------


class TestCheckExitCriteria:
    def test_passes_when_no_open_bugs_and_all_pass(self, tmp_path: Path) -> None:
        _setup_full_workspace(tmp_path)
        result = _check_exit_criteria(tmp_path)
        assert result.passed

    def test_fails_when_p0_bug_open(self, tmp_path: Path) -> None:
        _setup_full_workspace(tmp_path)
        add_bug(tmp_path, "Critical bug", priority="P0")
        result = _check_exit_criteria(tmp_path)
        assert not result.passed
        assert any("P0" in d and "✗" in d for d in result.details)

    def test_fails_when_tc_fail(self, tmp_path: Path) -> None:
        _setup_full_workspace(tmp_path)
        add_case(tmp_path, "Failing test", req_id="STORY-002")
        set_status(tmp_path, "TC-002", "ready")
        record_result(tmp_path, "TC-002", "fail")
        result = _check_exit_criteria(tmp_path)
        assert not result.passed

    def test_fails_when_no_strategy(self, tmp_path: Path) -> None:
        result = _check_exit_criteria(tmp_path)
        assert not result.passed
        assert any("strategy.yaml not found" in d for d in result.details)

    def test_closed_bugs_not_counted(self, tmp_path: Path) -> None:
        _setup_full_workspace(tmp_path)
        add_bug(tmp_path, "Fixed bug", priority="P0")
        for s in ("triaged", "in-progress", "fixed", "pending-retest", "verified", "closed"):
            set_bug_status(tmp_path, "BUG-001", s)
        result = _check_exit_criteria(tmp_path)
        assert result.passed

    def test_no_severity_rules_shows_warning(self, tmp_path: Path) -> None:
        create_strategy(tmp_path)
        path = tmp_path / ".testboat" / "draft" / "strategy.yaml"
        data = yaml.safe_load(path.read_text())
        data["metrics"]["severity"] = []
        path.write_text(yaml.dump(data))
        result = _check_exit_criteria(tmp_path)
        assert any("no severity rules" in d for d in result.details)


# ---------------------------------------------------------------------------
# ValidateReport
# ---------------------------------------------------------------------------


class TestValidateReport:
    def test_passed_when_all_checks_pass(self, tmp_path: Path) -> None:
        _setup_full_workspace(tmp_path)
        report = run_validate(tmp_path)
        assert report.passed

    def test_failed_when_any_check_fails(self, tmp_path: Path) -> None:
        # no strategy → check 1 fails
        add_case(tmp_path, "Test")
        report = run_validate(tmp_path)
        assert not report.passed

    def test_counts_correct(self, tmp_path: Path) -> None:
        _setup_full_workspace(tmp_path)
        report = run_validate(tmp_path)
        passed, total = report.counts
        assert total == 4
        assert passed == 4

    def test_has_four_checks(self, tmp_path: Path) -> None:
        _setup_full_workspace(tmp_path)
        report = run_validate(tmp_path)
        assert len(report.checks) == 4


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


class TestValidateCli:
    def test_exits_zero_on_full_pass(self, tmp_path: Path) -> None:
        _setup_full_workspace(tmp_path)
        result = runner.invoke(app, ["validate", str(tmp_path)])
        assert result.exit_code == 0
        assert "4/4 checks passed" in result.output

    def test_exits_one_on_failure(self, tmp_path: Path) -> None:
        add_case(tmp_path, "Test")  # no strategy
        result = runner.invoke(app, ["validate", str(tmp_path)])
        assert result.exit_code == 1

    def test_output_shows_check_names(self, tmp_path: Path) -> None:
        _setup_full_workspace(tmp_path)
        result = runner.invoke(app, ["validate", str(tmp_path)])
        assert "Format Validation" in result.output
        assert "Requirements Coverage" in result.output
        assert "Execution Completeness" in result.output
        assert "Exit Criteria" in result.output

    def test_output_shows_icons(self, tmp_path: Path) -> None:
        _setup_full_workspace(tmp_path)
        result = runner.invoke(app, ["validate", str(tmp_path)])
        assert "✓" in result.output
