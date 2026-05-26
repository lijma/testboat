"""Unit tests for ftest strategy commands — 100% coverage."""

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from ftest.cli import app
from ftest.commands.strategy import (
    STRATEGY_FILE,
    Strategy,
    StrategyStatus,
    TEMPLATE,
    _strategy_path,
    create_strategy,
    validate_strategy,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_strategy(ftest_root: Path, data: dict) -> Path:
    path = _strategy_path(ftest_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return path


def _valid_data() -> dict:
    return yaml.safe_load(yaml.dump(TEMPLATE))


# ---------------------------------------------------------------------------
# Schema models
# ---------------------------------------------------------------------------


class TestStrategySchema:
    def test_template_passes_validation(self) -> None:
        Strategy.model_validate(_valid_data())

    def test_invalid_likelihood_raises(self) -> None:
        data = _valid_data()
        data["risk_matrix"][0]["likelihood"] = "extreme"
        with pytest.raises(Exception):
            Strategy.model_validate(data)

    def test_invalid_status_raises(self) -> None:
        data = _valid_data()
        data["status"] = "unknown"
        with pytest.raises(Exception):
            Strategy.model_validate(data)

    def test_empty_risk_matrix_raises(self) -> None:
        data = _valid_data()
        data["risk_matrix"] = []
        with pytest.raises(Exception):
            Strategy.model_validate(data)

    def test_empty_severity_raises(self) -> None:
        data = _valid_data()
        data["metrics"]["severity"] = []
        with pytest.raises(Exception):
            Strategy.model_validate(data)

    def test_all_status_values_accepted(self) -> None:
        data = _valid_data()
        for status in StrategyStatus:
            data["status"] = status.value
            Strategy.model_validate(data)

    def test_missing_required_field_raises(self) -> None:
        data = _valid_data()
        del data["release"]
        with pytest.raises(Exception):
            Strategy.model_validate(data)


# ---------------------------------------------------------------------------
# create_strategy()
# ---------------------------------------------------------------------------


class TestCreateStrategy:
    def test_creates_strategy_file(self, tmp_path: Path) -> None:
        create_strategy(tmp_path)
        assert _strategy_path(tmp_path).exists()

    def test_file_is_valid_yaml(self, tmp_path: Path) -> None:
        create_strategy(tmp_path)
        data = yaml.safe_load(_strategy_path(tmp_path).read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_template_contains_required_keys(self, tmp_path: Path) -> None:
        create_strategy(tmp_path)
        data = yaml.safe_load(_strategy_path(tmp_path).read_text(encoding="utf-8"))
        for key in ("release", "status", "scope", "risk_matrix", "metrics"):
            assert key in data

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        create_strategy(tmp_path)
        assert _strategy_path(tmp_path).parent.is_dir()

    def test_returns_file_path(self, tmp_path: Path) -> None:
        path = create_strategy(tmp_path)
        assert path == _strategy_path(tmp_path)

    def test_idempotent_overwrites(self, tmp_path: Path) -> None:
        create_strategy(tmp_path)
        _strategy_path(tmp_path).write_text("old", encoding="utf-8")
        create_strategy(tmp_path)
        data = yaml.safe_load(_strategy_path(tmp_path).read_text(encoding="utf-8"))
        assert "release" in data


# ---------------------------------------------------------------------------
# validate_strategy()
# ---------------------------------------------------------------------------


class TestValidateStrategy:
    def test_valid_template_returns_no_errors(self, tmp_path: Path) -> None:
        create_strategy(tmp_path)
        assert validate_strategy(tmp_path) == []

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="strategy.yaml not found"):
            validate_strategy(tmp_path)

    def test_invalid_field_returns_errors(self, tmp_path: Path) -> None:
        data = _valid_data()
        data["status"] = "bad-status"
        _write_strategy(tmp_path, data)
        errors = validate_strategy(tmp_path)
        assert len(errors) > 0

    def test_error_message_contains_field_name(self, tmp_path: Path) -> None:
        data = _valid_data()
        data["risk_matrix"] = []
        _write_strategy(tmp_path, data)
        errors = validate_strategy(tmp_path)
        assert any("risk_matrix" in e for e in errors)

    def test_multiple_errors_all_reported(self, tmp_path: Path) -> None:
        data = _valid_data()
        data["status"] = "bad"
        data["risk_matrix"] = []
        _write_strategy(tmp_path, data)
        errors = validate_strategy(tmp_path)
        assert len(errors) >= 2


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


class TestStrategyCreateCli:
    def test_create_exits_zero(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["strategy", "create", str(tmp_path)])
        assert result.exit_code == 0

    def test_create_shows_file_path(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["strategy", "create", str(tmp_path)])
        assert STRATEGY_FILE in result.output

    def test_create_shows_next_step_hint(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["strategy", "create", str(tmp_path)])
        assert "validate" in result.output

    def test_create_idempotent(self, tmp_path: Path) -> None:
        runner.invoke(app, ["strategy", "create", str(tmp_path)])
        result = runner.invoke(app, ["strategy", "create", str(tmp_path)])
        assert result.exit_code == 0

    def test_create_fails_on_non_directory(self, tmp_path: Path) -> None:
        f = tmp_path / "x.txt"
        f.write_text("x")
        result = runner.invoke(app, ["strategy", "create", str(f)])
        assert result.exit_code == 1
        assert "not a directory" in result.output


class TestStrategyValidateCli:
    def test_validate_passes_on_template(self, tmp_path: Path) -> None:
        runner.invoke(app, ["strategy", "create", str(tmp_path)])
        result = runner.invoke(app, ["strategy", "validate", str(tmp_path)])
        assert result.exit_code == 0
        assert "valid" in result.output

    def test_validate_fails_when_no_file(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["strategy", "validate", str(tmp_path)])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_validate_fails_on_bad_schema(self, tmp_path: Path) -> None:
        data = _valid_data()
        data["status"] = "garbage"
        _write_strategy(tmp_path, data)
        result = runner.invoke(app, ["strategy", "validate", str(tmp_path)])
        assert result.exit_code == 1
        assert "FAILED" in result.output

    def test_validate_reports_each_error(self, tmp_path: Path) -> None:
        data = _valid_data()
        data["risk_matrix"] = []
        _write_strategy(tmp_path, data)
        result = runner.invoke(app, ["strategy", "validate", str(tmp_path)])
        assert "✗" in result.output
