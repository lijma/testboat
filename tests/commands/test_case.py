"""Unit tests for ftest case command — 100% coverage."""

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from ftest.cli import app
from ftest.commands.case import (
    CaseModel,
    CaseStatus,
    _case_path,
    _next_id,
    _valid_transition,
    add_case,
    list_cases,
    set_status,
    show_case,
    validate_case,
    validate_cases_batch,
)
from ftest.commands.tag import add_tag

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup_tags(root: Path) -> None:
    add_tag(root, "sprint", "v1.0.0")
    add_tag(root, "type", "functional")
    add_tag(root, "module", "auth")


def _make_case(root: Path, **kwargs) -> Path:
    _setup_tags(root)
    return add_case(root, "Test login", sprint="v1.0.0",
                    type_="functional", module="auth", **kwargs)


def _full_case(root: Path) -> Path:
    path = _make_case(root)
    tc_id = path.stem
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["steps"] = [{"action": "do something", "expected": "result"}]
    data["expected_result"] = "all good"
    path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------


class TestValidTransition:
    def test_draft_to_ready(self) -> None:
        assert _valid_transition(CaseStatus.draft, CaseStatus.ready)

    def test_draft_to_pass_invalid(self) -> None:
        assert not _valid_transition(CaseStatus.draft, CaseStatus.pass_)

    def test_ready_to_all_outcomes(self) -> None:
        for target in (CaseStatus.pass_, CaseStatus.fail,
                       CaseStatus.blocked, CaseStatus.skipped, CaseStatus.draft):
            assert _valid_transition(CaseStatus.ready, target)

    def test_pass_to_ready(self) -> None:
        assert _valid_transition(CaseStatus.pass_, CaseStatus.ready)

    def test_pass_to_draft_invalid(self) -> None:
        assert not _valid_transition(CaseStatus.pass_, CaseStatus.draft)


# ---------------------------------------------------------------------------
# _next_id
# ---------------------------------------------------------------------------


class TestNextId:
    def test_first_case_is_tc001(self, tmp_path: Path) -> None:
        assert _next_id(tmp_path) == "TC-001"

    def test_increments_from_existing(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        assert _next_id(tmp_path) == "TC-002"

    def test_pads_to_three_digits(self, tmp_path: Path) -> None:
        for _ in range(9):
            _make_case(tmp_path)
        assert _next_id(tmp_path) == "TC-010"


# ---------------------------------------------------------------------------
# add_case
# ---------------------------------------------------------------------------


class TestAddCase:
    def test_creates_yaml_file(self, tmp_path: Path) -> None:
        path = _make_case(tmp_path)
        assert path.exists()

    def test_file_stem_is_tc_id(self, tmp_path: Path) -> None:
        path = _make_case(tmp_path)
        assert path.stem == "TC-001"

    def test_status_is_draft(self, tmp_path: Path) -> None:
        path = _make_case(tmp_path)
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["status"] == "draft"

    def test_tags_stored(self, tmp_path: Path) -> None:
        path = _make_case(tmp_path)
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["tags"]["sprint"] == "v1.0.0"
        assert data["tags"]["type"] == "functional"
        assert data["tags"]["module"] == "auth"

    def test_steps_empty_on_create(self, tmp_path: Path) -> None:
        path = _make_case(tmp_path)
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["steps"] == []

    def test_raises_if_tag_not_registered(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            add_case(tmp_path, "title", sprint="unknown-sprint")

    def test_no_tags_allowed(self, tmp_path: Path) -> None:
        path = add_case(tmp_path, "no tags case")
        assert path.exists()

    def test_req_id_stored(self, tmp_path: Path) -> None:
        path = _make_case(tmp_path, req_id="STORY-011")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["req_id"] == "STORY-011"


# ---------------------------------------------------------------------------
# list_cases
# ---------------------------------------------------------------------------


class TestListCases:
    def test_returns_all_cases(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        _make_case(tmp_path)
        assert len(list_cases(tmp_path)) == 2

    def test_empty_when_no_cases(self, tmp_path: Path) -> None:
        assert list_cases(tmp_path) == []

    def test_filter_by_sprint(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        add_tag(tmp_path, "sprint", "v2.0.0")
        add_case(tmp_path, "other", sprint="v2.0.0")
        result = list_cases(tmp_path, sprint="v1.0.0")
        assert len(result) == 1
        assert result[0]["tags"]["sprint"] == "v1.0.0"

    def test_filter_by_type_excludes_non_matching(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        add_case(tmp_path, "other")          # no type tag
        result = list_cases(tmp_path, type_="functional")
        assert len(result) == 1
        assert result[0]["tags"]["type"] == "functional"

    def test_filter_by_module_excludes_non_matching(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        add_case(tmp_path, "other")          # no module tag
        result = list_cases(tmp_path, module="auth")
        assert len(result) == 1
        assert result[0]["tags"]["module"] == "auth"

    def test_filter_by_status(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        assert len(list_cases(tmp_path, status="draft")) == 1
        assert len(list_cases(tmp_path, status="ready")) == 0

    def test_no_filter_returns_all(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        _make_case(tmp_path)
        assert len(list_cases(tmp_path)) == 2


# ---------------------------------------------------------------------------
# show_case
# ---------------------------------------------------------------------------


class TestShowCase:
    def test_returns_case_data(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        data = show_case(tmp_path, "TC-001")
        assert data["id"] == "TC-001"

    def test_raises_if_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            show_case(tmp_path, "TC-999")


# ---------------------------------------------------------------------------
# set_status
# ---------------------------------------------------------------------------


class TestSetStatus:
    def test_valid_transition(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        set_status(tmp_path, "TC-001", "ready")
        data = yaml.safe_load(_case_path(tmp_path, "TC-001").read_text(encoding="utf-8"))
        assert data["status"] == "ready"

    def test_invalid_transition_raises(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        with pytest.raises(ValueError, match="Cannot transition"):
            set_status(tmp_path, "TC-001", "pass")

    def test_unknown_status_raises(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        with pytest.raises(ValueError, match="Unknown status"):
            set_status(tmp_path, "TC-001", "flying")

    def test_not_found_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            set_status(tmp_path, "TC-999", "ready")


# ---------------------------------------------------------------------------
# validate_case
# ---------------------------------------------------------------------------


class TestValidateCase:
    def test_draft_with_empty_steps_valid(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        assert validate_case(tmp_path, "TC-001") == []

    def test_full_case_valid(self, tmp_path: Path) -> None:
        _full_case(tmp_path)
        assert validate_case(tmp_path, "TC-001") == []

    def test_invalid_tag_ref_reported(self, tmp_path: Path) -> None:
        path = _make_case(tmp_path)
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["tags"]["sprint"] = "nonexistent"
        path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
        errors = validate_case(tmp_path, "TC-001")
        assert any("sprint" in e for e in errors)

    def test_non_draft_without_steps_reported(self, tmp_path: Path) -> None:
        path = _make_case(tmp_path)
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["status"] = "ready"
        path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
        errors = validate_case(tmp_path, "TC-001")
        assert any("steps" in e for e in errors)

    def test_not_found_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            validate_case(tmp_path, "TC-999")

    def test_bad_schema_reported(self, tmp_path: Path) -> None:
        path = _make_case(tmp_path)
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["priority"] = "X9"
        path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
        errors = validate_case(tmp_path, "TC-001")
        assert len(errors) > 0


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


class TestCaseCli:
    def test_add_creates_case(self, tmp_path: Path) -> None:
        runner.invoke(app, ["tag", "add", "sprint", "v1.0.0", "--workspace", str(tmp_path)])
        result = runner.invoke(app, ["case", "add", "--title", "Login test",
                                     "--sprint", "v1.0.0", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "TC-001" in result.output

    def test_add_unknown_tag_exits_one(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["case", "add", "--title", "x",
                                     "--sprint", "ghost", "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_list_empty(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["case", "list", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "No test cases" in result.output

    def test_list_shows_cases(self, tmp_path: Path) -> None:
        runner.invoke(app, ["tag", "add", "sprint", "v1.0.0", "--workspace", str(tmp_path)])
        runner.invoke(app, ["case", "add", "--title", "Login test",
                             "--sprint", "v1.0.0", "--workspace", str(tmp_path)])
        result = runner.invoke(app, ["case", "list", "--workspace", str(tmp_path)])
        assert "TC-001" in result.output

    def test_show_case(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        result = runner.invoke(app, ["case", "show", "TC-001", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "TC-001" in result.output

    def test_show_not_found(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["case", "show", "TC-999", "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_status_transition(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        result = runner.invoke(app, ["case", "status", "TC-001", "ready",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "ready" in result.output

    def test_status_invalid_transition(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        result = runner.invoke(app, ["case", "status", "TC-001", "pass",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_validate_valid_case(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        result = runner.invoke(app, ["case", "validate", "TC-001", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "valid ✓" in result.output

    def test_validate_not_found(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["case", "validate", "TC-999", "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_validate_shows_errors(self, tmp_path: Path) -> None:
        path = _make_case(tmp_path)
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["tags"]["sprint"] = "missing-sprint"
        path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
        result = runner.invoke(app, ["case", "validate", "TC-001", "--workspace", str(tmp_path)])
        assert result.exit_code == 1
        assert "FAILED" in result.output
        assert "✗" in result.output

    # -- batch validate: 'all' keyword --

    def test_validate_all_exits_zero_when_all_valid(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        _make_case(tmp_path)
        result = runner.invoke(app, ["case", "validate", "all", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "2/2 valid" in result.output

    def test_validate_all_exits_one_when_any_failed(self, tmp_path: Path) -> None:
        path = _make_case(tmp_path)
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["tags"]["sprint"] = "ghost"
        path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
        result = runner.invoke(app, ["case", "validate", "all", "--workspace", str(tmp_path)])
        assert result.exit_code == 1
        assert "0/1 valid" in result.output

    def test_validate_all_shows_per_case_result(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        result = runner.invoke(app, ["case", "validate", "all", "--workspace", str(tmp_path)])
        assert "TC-001 ✓" in result.output

    def test_validate_all_no_cases(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["case", "validate", "all", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "No test cases" in result.output

    # -- batch validate: tag filters --

    def test_validate_by_module_filter(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        result = runner.invoke(app, ["case", "validate", "all",
                                     "--module", "auth", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "TC-001 ✓" in result.output

    def test_validate_by_sprint_filter(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        result = runner.invoke(app, ["case", "validate", "all",
                                     "--sprint", "v1.0.0", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "1/1 valid" in result.output

    def test_validate_by_type_filter(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        result = runner.invoke(app, ["case", "validate", "all",
                                     "--type", "functional", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "1/1 valid" in result.output


# ---------------------------------------------------------------------------
# validate_cases_batch()
# ---------------------------------------------------------------------------


class TestValidateCasesBatch:
    def test_returns_dict_keyed_by_id(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        _make_case(tmp_path)
        results = validate_cases_batch(tmp_path)
        assert "TC-001" in results
        assert "TC-002" in results

    def test_valid_cases_have_empty_error_list(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        results = validate_cases_batch(tmp_path)
        assert results["TC-001"] == []

    def test_invalid_case_has_errors(self, tmp_path: Path) -> None:
        path = _make_case(tmp_path)
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["tags"]["sprint"] = "ghost"
        path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
        results = validate_cases_batch(tmp_path)
        assert len(results["TC-001"]) > 0

    def test_empty_when_no_cases(self, tmp_path: Path) -> None:
        assert validate_cases_batch(tmp_path) == {}

    def test_filter_by_module(self, tmp_path: Path) -> None:
        _make_case(tmp_path)
        add_case(tmp_path, "no module")
        results = validate_cases_batch(tmp_path, module="auth")
        assert list(results.keys()) == ["TC-001"]
