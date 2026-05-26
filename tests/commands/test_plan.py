"""Unit tests for testboat plan command — 100% coverage."""

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from testboat.cli import app
from testboat.commands.plan import (
    AutomationTool,
    ExecutionType,
    Plan,
    PlanStatus,
    TOOL_RUN_COMMANDS,
    _automate_root,
    _plan_path,
    create_plan,
    get_run_command,
    list_plans,
    register_automation,
    set_plan_status,
    show_plan,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# create_plan
# ---------------------------------------------------------------------------


class TestCreatePlan:
    def test_creates_plan_file(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        assert _plan_path(tmp_path, "TC-001").exists()

    def test_default_execution_type_manual(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        data = yaml.safe_load(_plan_path(tmp_path, "TC-001").read_text())
        assert data["execution_type"] == "manual"
        assert data["automation_tool"] is None

    def test_automated_sets_default_tool(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", execution_type="automated")
        data = yaml.safe_load(_plan_path(tmp_path, "TC-001").read_text())
        assert data["automation_tool"] == "playwright"
        assert data["automation_path"] is not None

    def test_automated_with_explicit_tool(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", execution_type="automated", tool="jmeter")
        data = yaml.safe_load(_plan_path(tmp_path, "TC-001").read_text())
        assert data["automation_tool"] == "jmeter"

    def test_both_type(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", execution_type="both")
        data = yaml.safe_load(_plan_path(tmp_path, "TC-001").read_text())
        assert data["execution_type"] == "both"
        assert data["automation_tool"] == "playwright"

    def test_status_is_draft(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        data = yaml.safe_load(_plan_path(tmp_path, "TC-001").read_text())
        assert data["status"] == "draft"

    def test_idempotent(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        create_plan(tmp_path, "TC-001", execution_type="automated")
        data = yaml.safe_load(_plan_path(tmp_path, "TC-001").read_text())
        assert data["execution_type"] == "automated"

    def test_invalid_execution_type_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Invalid execution_type"):
            create_plan(tmp_path, "TC-001", execution_type="flying")

    def test_invalid_tool_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Invalid tool"):
            create_plan(tmp_path, "TC-001", execution_type="automated", tool="magic")

    def test_returns_path(self, tmp_path: Path) -> None:
        path = create_plan(tmp_path, "TC-001")
        assert path == _plan_path(tmp_path, "TC-001")

    def test_executor_stored(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", executor="tester-1")
        data = yaml.safe_load(_plan_path(tmp_path, "TC-001").read_text())
        assert data["executor"] == "tester-1"

    def test_notes_stored(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", notes="needs VPN")
        data = yaml.safe_load(_plan_path(tmp_path, "TC-001").read_text())
        assert data["notes"] == "needs VPN"

    def test_all_automation_tools_accepted(self, tmp_path: Path) -> None:
        for i, tool in enumerate(AutomationTool):
            create_plan(tmp_path, f"TC-{i:03d}", execution_type="automated", tool=tool.value)


# ---------------------------------------------------------------------------
# list_plans
# ---------------------------------------------------------------------------


class TestListPlans:
    def test_returns_all_plans(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        create_plan(tmp_path, "TC-002")
        assert len(list_plans(tmp_path)) == 2

    def test_empty_when_no_plans(self, tmp_path: Path) -> None:
        assert list_plans(tmp_path) == []

    def test_filter_by_execution_type(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", execution_type="manual")
        create_plan(tmp_path, "TC-002", execution_type="automated")
        assert len(list_plans(tmp_path, execution_type="manual")) == 1

    def test_filter_by_status(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        set_plan_status(tmp_path, "TC-001", "approved")
        assert len(list_plans(tmp_path, status="approved")) == 1
        assert len(list_plans(tmp_path, status="draft")) == 0


# ---------------------------------------------------------------------------
# show_plan / set_plan_status
# ---------------------------------------------------------------------------


class TestShowPlan:
    def test_returns_plan_data(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        data = show_plan(tmp_path, "TC-001")
        assert data["tc_id"] == "TC-001"

    def test_raises_if_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            show_plan(tmp_path, "TC-999")


class TestSetPlanStatus:
    def test_valid_status_transition(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        set_plan_status(tmp_path, "TC-001", "approved")
        data = yaml.safe_load(_plan_path(tmp_path, "TC-001").read_text())
        assert data["status"] == "approved"

    def test_invalid_status_raises(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        with pytest.raises(ValueError, match="Invalid status"):
            set_plan_status(tmp_path, "TC-001", "flying")

    def test_not_found_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            set_plan_status(tmp_path, "TC-999", "approved")


# ---------------------------------------------------------------------------
# get_run_command
# ---------------------------------------------------------------------------


class TestGetRunCommand:
    def test_returns_tool_and_command(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", execution_type="automated", tool="playwright")
        tool, cmd = get_run_command(tmp_path, "TC-001")
        assert tool == "playwright"
        assert "playwright" in cmd

    def test_raises_if_no_automation(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", execution_type="manual")
        with pytest.raises(ValueError, match="no automation"):
            get_run_command(tmp_path, "TC-001")

    def test_raises_if_plan_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            get_run_command(tmp_path, "TC-999")

    def test_all_tools_have_commands(self, tmp_path: Path) -> None:
        for tool in AutomationTool:
            assert tool.value in TOOL_RUN_COMMANDS


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestPlanCli:
    def test_create_exits_zero(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["plan", "create", "TC-001", "--workspace", str(tmp_path)])
        assert result.exit_code == 0

    def test_create_shows_path(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["plan", "create", "TC-001", "--workspace", str(tmp_path)])
        assert "TC-001-plan.yaml" in result.output

    def test_create_invalid_type_exits_one(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["plan", "create", "TC-001", "--type", "flying",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_list_empty(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["plan", "list", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "No plans" in result.output

    def test_list_shows_plans(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        result = runner.invoke(app, ["plan", "list", "--workspace", str(tmp_path)])
        assert "TC-001" in result.output

    def test_show_plan(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        result = runner.invoke(app, ["plan", "show", "TC-001", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "tc_id" in result.output

    def test_show_not_found(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["plan", "show", "TC-999", "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_status_transition(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        result = runner.invoke(app, ["plan", "status", "TC-001", "approved",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "approved" in result.output

    def test_status_invalid_exits_one(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        result = runner.invoke(app, ["plan", "status", "TC-001", "flying",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_status_not_found_exits_one(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["plan", "status", "TC-999", "approved",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_register_exits_zero(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        result = runner.invoke(app, ["plan", "register", "TC-001",
                                     ".testboat/draft/automate/pytest/tests/test_TC001.py",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "pytest" in result.output

    def test_register_not_found_exits_one(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["plan", "register", "TC-999",
                                     "some/script.py", "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_register_invalid_tool_exits_one(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        result = runner.invoke(app, ["plan", "register", "TC-001",
                                     "script.py", "--tool", "magic",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# register_automation
# ---------------------------------------------------------------------------


class TestRegisterAutomation:
    def test_registers_script_path(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        register_automation(tmp_path, "TC-001", ".testboat/draft/automate/pytest/tests/test_TC001.py")
        data = yaml.safe_load(_plan_path(tmp_path, "TC-001").read_text())
        assert data["automation_path"] == ".testboat/draft/automate/pytest/tests/test_TC001.py"

    def test_infers_pytest_from_py_extension(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        register_automation(tmp_path, "TC-001", "tests/test_TC001.py")
        data = yaml.safe_load(_plan_path(tmp_path, "TC-001").read_text())
        assert data["automation_tool"] == "pytest"

    def test_infers_playwright_from_ts_extension(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        register_automation(tmp_path, "TC-001", "tests/TC-001.spec.ts")
        data = yaml.safe_load(_plan_path(tmp_path, "TC-001").read_text())
        assert data["automation_tool"] == "playwright"

    def test_infers_playwright_from_js_extension(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        register_automation(tmp_path, "TC-001", "tests/TC-001.spec.js")
        data = yaml.safe_load(_plan_path(tmp_path, "TC-001").read_text())
        assert data["automation_tool"] == "playwright"

    def test_infers_jmeter_from_jmx(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        register_automation(tmp_path, "TC-001", "TC-001/test.jmx")
        data = yaml.safe_load(_plan_path(tmp_path, "TC-001").read_text())
        assert data["automation_tool"] == "jmeter"

    def test_infers_maestro_from_yaml(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        register_automation(tmp_path, "TC-001", "TC-001/flow.yaml")
        data = yaml.safe_load(_plan_path(tmp_path, "TC-001").read_text())
        assert data["automation_tool"] == "maestro"

    def test_infers_maestro_from_yml(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        register_automation(tmp_path, "TC-001", "TC-001/flow.yml")
        data = yaml.safe_load(_plan_path(tmp_path, "TC-001").read_text())
        assert data["automation_tool"] == "maestro"

    def test_defaults_bash_for_unknown_extension(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        register_automation(tmp_path, "TC-001", "TC-001/test.rb")
        data = yaml.safe_load(_plan_path(tmp_path, "TC-001").read_text())
        assert data["automation_tool"] == "bash"

    def test_explicit_tool_overrides_inference(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        register_automation(tmp_path, "TC-001", "tests/test.py", tool="bash")
        data = yaml.safe_load(_plan_path(tmp_path, "TC-001").read_text())
        assert data["automation_tool"] == "bash"

    def test_invalid_explicit_tool_raises(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        with pytest.raises(ValueError, match="Invalid tool"):
            register_automation(tmp_path, "TC-001", "test.py", tool="magic")

    def test_upgrades_manual_plan_to_automated(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", execution_type="manual")
        register_automation(tmp_path, "TC-001", "test.py")
        data = yaml.safe_load(_plan_path(tmp_path, "TC-001").read_text())
        assert data["execution_type"] == "automated"

    def test_does_not_downgrade_both_to_automated(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001", execution_type="both")
        register_automation(tmp_path, "TC-001", "test.py")
        data = yaml.safe_load(_plan_path(tmp_path, "TC-001").read_text())
        assert data["execution_type"] == "both"

    def test_raises_if_plan_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            register_automation(tmp_path, "TC-999", "test.py")

    def test_returns_plan_path(self, tmp_path: Path) -> None:
        create_plan(tmp_path, "TC-001")
        result = register_automation(tmp_path, "TC-001", "test.py")
        assert result == _plan_path(tmp_path, "TC-001")


class TestAutomateRoot:
    def test_automate_root_in_executions(self, tmp_path: Path) -> None:
        root = _automate_root(tmp_path)
        assert ".testboat/draft/executions/automate" in str(root)
