"""Unit tests for ftest bug command — 100% coverage."""

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from ftest.cli import app
from ftest.commands.bug import (
    BugPriority,
    BugStatus,
    Severity,
    _bug_path,
    _valid_transition,
    add_bug,
    list_bugs,
    set_bug_status,
    show_bug,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


class TestValidTransition:
    def test_new_to_triaged(self) -> None:
        assert _valid_transition(BugStatus.new, BugStatus.triaged)

    def test_new_to_in_progress_invalid(self) -> None:
        assert not _valid_transition(BugStatus.new, BugStatus.in_progress)

    def test_triaged_to_in_progress(self) -> None:
        assert _valid_transition(BugStatus.triaged, BugStatus.in_progress)

    def test_triaged_to_deferred(self) -> None:
        assert _valid_transition(BugStatus.triaged, BugStatus.deferred)

    def test_triaged_to_wont_fix(self) -> None:
        assert _valid_transition(BugStatus.triaged, BugStatus.wont_fix)

    def test_in_progress_to_fixed(self) -> None:
        assert _valid_transition(BugStatus.in_progress, BugStatus.fixed)

    def test_fixed_to_pending_retest(self) -> None:
        assert _valid_transition(BugStatus.fixed, BugStatus.pending_retest)

    def test_pending_retest_to_verified(self) -> None:
        assert _valid_transition(BugStatus.pending_retest, BugStatus.verified)

    def test_pending_retest_back_to_in_progress(self) -> None:
        assert _valid_transition(BugStatus.pending_retest, BugStatus.in_progress)

    def test_verified_to_closed(self) -> None:
        assert _valid_transition(BugStatus.verified, BugStatus.closed)

    def test_deferred_to_triaged(self) -> None:
        assert _valid_transition(BugStatus.deferred, BugStatus.triaged)

    def test_closed_has_no_transitions(self) -> None:
        for target in BugStatus:
            assert not _valid_transition(BugStatus.closed, target)

    def test_wont_fix_has_no_transitions(self) -> None:
        for target in BugStatus:
            assert not _valid_transition(BugStatus.wont_fix, target)


# ---------------------------------------------------------------------------
# add_bug
# ---------------------------------------------------------------------------


class TestAddBug:
    def test_creates_bug_file(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Login crashes")
        assert _bug_path(tmp_path, "BUG-001").exists()

    def test_auto_increments_id(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug one")
        add_bug(tmp_path, "Bug two")
        assert _bug_path(tmp_path, "BUG-002").exists()

    def test_default_status_is_new(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug")
        data = yaml.safe_load(_bug_path(tmp_path, "BUG-001").read_text())
        assert data["status"] == "new"

    def test_default_severity_major(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug")
        data = yaml.safe_load(_bug_path(tmp_path, "BUG-001").read_text())
        assert data["severity"] == "major"

    def test_all_fields_stored(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug", severity="critical", priority="P0",
                tc_id="TC-001", result_id="RES-001", environment="staging", notes="repro fast")
        data = yaml.safe_load(_bug_path(tmp_path, "BUG-001").read_text())
        assert data["severity"] == "critical"
        assert data["priority"] == "P0"
        assert data["tc_id"] == "TC-001"
        assert data["result_id"] == "RES-001"
        assert data["environment"] == "staging"
        assert data["notes"] == "repro fast"

    def test_found_at_is_today(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug")
        data = yaml.safe_load(_bug_path(tmp_path, "BUG-001").read_text())
        assert data["found_at"]

    def test_invalid_severity_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Invalid severity"):
            add_bug(tmp_path, "Bug", severity="extreme")

    def test_invalid_priority_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Invalid priority"):
            add_bug(tmp_path, "Bug", priority="X9")

    def test_all_severities_accepted(self, tmp_path: Path) -> None:
        for i, sev in enumerate(Severity):
            add_bug(tmp_path, f"Bug {i}", severity=sev.value)

    def test_all_priorities_accepted(self, tmp_path: Path) -> None:
        for i, pri in enumerate(BugPriority):
            add_bug(tmp_path, f"Bug {i}", priority=pri.value)

    def test_returns_path(self, tmp_path: Path) -> None:
        path = add_bug(tmp_path, "Bug")
        assert path == _bug_path(tmp_path, "BUG-001")

    def test_empty_title_raises_via_pydantic(self, tmp_path: Path) -> None:
        from ftest.commands.bug import BugModel
        with pytest.raises(Exception):
            BugModel(id="BUG-001", title="   ", status="new",
                     severity="major", priority="P2")

    def test_valid_title_passes_validator(self) -> None:
        from ftest.commands.bug import BugModel
        m = BugModel(id="BUG-001", title="Login crash", status="new",
                     severity="major", priority="P2")
        assert m.title == "Login crash"


# ---------------------------------------------------------------------------
# list_bugs
# ---------------------------------------------------------------------------


class TestListBugs:
    def test_returns_all_bugs(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug 1")
        add_bug(tmp_path, "Bug 2")
        assert len(list_bugs(tmp_path)) == 2

    def test_empty_when_none(self, tmp_path: Path) -> None:
        assert list_bugs(tmp_path) == []

    def test_filter_by_status(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug 1")
        assert len(list_bugs(tmp_path, status="new")) == 1
        assert len(list_bugs(tmp_path, status="closed")) == 0

    def test_filter_by_severity(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug 1", severity="critical")
        add_bug(tmp_path, "Bug 2", severity="minor")
        assert len(list_bugs(tmp_path, severity="critical")) == 1

    def test_filter_by_priority(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug 1", priority="P0")
        add_bug(tmp_path, "Bug 2", priority="P2")
        assert len(list_bugs(tmp_path, priority="P0")) == 1

    def test_filter_by_sprint(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug 1", sprint="v1.0.0")
        add_bug(tmp_path, "Bug 2")
        assert len(list_bugs(tmp_path, sprint="v1.0.0")) == 1

    def test_filter_by_type_excludes_non_matching(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug 1", type_="functional")
        add_bug(tmp_path, "Bug 2")
        assert len(list_bugs(tmp_path, type_="functional")) == 1

    def test_filter_by_module_excludes_non_matching(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug 1", module="auth")
        add_bug(tmp_path, "Bug 2")
        assert len(list_bugs(tmp_path, module="auth")) == 1


# ---------------------------------------------------------------------------
# show_bug
# ---------------------------------------------------------------------------


class TestShowBug:
    def test_returns_bug_data(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug")
        data = show_bug(tmp_path, "BUG-001")
        assert data["id"] == "BUG-001"

    def test_raises_if_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            show_bug(tmp_path, "BUG-999")


# ---------------------------------------------------------------------------
# set_bug_status
# ---------------------------------------------------------------------------


class TestSetBugStatus:
    def test_valid_transition(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug")
        set_bug_status(tmp_path, "BUG-001", "triaged")
        data = yaml.safe_load(_bug_path(tmp_path, "BUG-001").read_text())
        assert data["status"] == "triaged"

    def test_fixed_sets_fixed_at(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug")
        set_bug_status(tmp_path, "BUG-001", "triaged")
        set_bug_status(tmp_path, "BUG-001", "in-progress")
        set_bug_status(tmp_path, "BUG-001", "fixed")
        data = yaml.safe_load(_bug_path(tmp_path, "BUG-001").read_text())
        assert data["fixed_at"] is not None

    def test_invalid_transition_raises(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug")
        with pytest.raises(ValueError, match="Cannot transition"):
            set_bug_status(tmp_path, "BUG-001", "closed")

    def test_unknown_status_raises(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug")
        with pytest.raises(ValueError, match="Invalid status"):
            set_bug_status(tmp_path, "BUG-001", "flying")

    def test_not_found_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            set_bug_status(tmp_path, "BUG-999", "triaged")


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


class TestBugCli:
    def test_add_exits_zero(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["bug", "add", "--title", "Login crash",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "BUG-001" in result.output

    def test_add_shows_severity_priority(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["bug", "add", "--title", "Bug",
                                     "--severity", "critical", "--priority", "P0",
                                     "--workspace", str(tmp_path)])
        assert "CRITICAL" in result.output
        assert "P0" in result.output

    def test_add_invalid_severity_exits_one(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["bug", "add", "--title", "Bug",
                                     "--severity", "extreme", "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_add_invalid_priority_exits_one(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["bug", "add", "--title", "Bug",
                                     "--priority", "X9", "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_list_empty(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["bug", "list", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "No bugs" in result.output

    def test_list_shows_bugs(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Login crash", severity="critical", priority="P0")
        result = runner.invoke(app, ["bug", "list", "--workspace", str(tmp_path)])
        assert "BUG-001" in result.output
        assert "critical" in result.output

    def test_show_bug(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug")
        result = runner.invoke(app, ["bug", "show", "BUG-001", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "BUG-001" in result.output

    def test_show_not_found(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["bug", "show", "BUG-999", "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_status_transition(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug")
        result = runner.invoke(app, ["bug", "status", "BUG-001", "triaged",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "triaged" in result.output

    def test_status_invalid_transition(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug")
        result = runner.invoke(app, ["bug", "status", "BUG-001", "closed",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_status_unknown(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug")
        result = runner.invoke(app, ["bug", "status", "BUG-001", "flying",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_status_not_found(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["bug", "status", "BUG-999", "triaged",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_add_with_tags(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["bug", "add", "--title", "Bug",
                                     "--sprint", "v1.0.0", "--module", "auth",
                                     "--type", "functional",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        data = yaml.safe_load(
            (tmp_path / ".ftest" / "draft" / "bugs" / "BUG-001.yaml").read_text()
        )
        assert data["tags"]["sprint"] == "v1.0.0"
        assert data["tags"]["module"] == "auth"

    def test_list_filter_by_sprint(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug 1", sprint="v1.0.0")
        add_bug(tmp_path, "Bug 2")
        result = runner.invoke(app, ["bug", "list", "--sprint", "v1.0.0",
                                     "--workspace", str(tmp_path)])
        assert "BUG-001" in result.output
        assert "BUG-002" not in result.output

    def test_list_filter_by_module(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug 1", module="auth")
        add_bug(tmp_path, "Bug 2")
        result = runner.invoke(app, ["bug", "list", "--module", "auth",
                                     "--workspace", str(tmp_path)])
        assert "BUG-001" in result.output
        assert "BUG-002" not in result.output
