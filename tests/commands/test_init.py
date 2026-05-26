"""Unit tests for ftest init command — 100% coverage."""

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from ftest.cli import app
from ftest.commands.init import (
    DRAFT_DIR,
    DRAFT_SUBDIRS,
    FTEST_DIR,
    _default_config,
    init_workspace,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# init_workspace() — pure logic
# ---------------------------------------------------------------------------


class TestInitWorkspace:
    def test_creates_ftest_dir(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        assert (tmp_path / FTEST_DIR).is_dir()

    def test_creates_draft_dir(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        assert (tmp_path / FTEST_DIR / DRAFT_DIR).is_dir()

    def test_creates_all_subdirs(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        draft = tmp_path / FTEST_DIR / DRAFT_DIR
        for subdir in DRAFT_SUBDIRS:
            assert (draft / subdir).is_dir(), f"missing: {subdir}"

    def test_creates_config_yaml(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        assert (tmp_path / FTEST_DIR / DRAFT_DIR / "ftest.yaml").is_file()

    def test_config_yaml_content(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        data = yaml.safe_load(
            (tmp_path / FTEST_DIR / DRAFT_DIR / "ftest.yaml").read_text(encoding="utf-8")
        )
        assert data["version"] == "draft"
        assert data["workspace"] == str(tmp_path)
        assert data["created_by"] == "ftest init"

    def test_returns_ftest_path(self, tmp_path: Path) -> None:
        assert init_workspace(tmp_path) == tmp_path / FTEST_DIR

    def test_idempotent_second_run_succeeds(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        init_workspace(tmp_path)  # must not raise
        assert (tmp_path / FTEST_DIR / DRAFT_DIR).is_dir()

    def test_idempotent_preserves_extra_files(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        extra = tmp_path / FTEST_DIR / DRAFT_DIR / "cases" / "TC-001.yaml"
        extra.write_text("id: TC-001", encoding="utf-8")
        init_workspace(tmp_path)
        assert extra.exists()

    def test_idempotent_refreshes_config(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        config = tmp_path / FTEST_DIR / DRAFT_DIR / "ftest.yaml"
        config.write_text("corrupted", encoding="utf-8")
        init_workspace(tmp_path)
        data = yaml.safe_load(config.read_text(encoding="utf-8"))
        assert data["version"] == "draft"


# ---------------------------------------------------------------------------
# _default_config() helper
# ---------------------------------------------------------------------------


class TestDefaultConfig:
    def test_returns_required_keys(self, tmp_path: Path) -> None:
        cfg = _default_config(tmp_path)
        assert cfg["version"] == "draft"
        assert cfg["workspace"] == str(tmp_path)
        assert cfg["created_by"] == "ftest init"


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


class TestInitCli:
    def test_cli_with_explicit_workspace(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["init", str(tmp_path)])
        assert result.exit_code == 0
        assert "Initialized ftest workspace" in result.output

    def test_cli_output_lists_subdirs(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["init", str(tmp_path)])
        for subdir in DRAFT_SUBDIRS:
            assert subdir in result.output

    def test_cli_output_mentions_config(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["init", str(tmp_path)])
        assert "ftest.yaml" in result.output

    def test_cli_idempotent_second_run(self, tmp_path: Path) -> None:
        runner.invoke(app, ["init", str(tmp_path)])
        result = runner.invoke(app, ["init", str(tmp_path)])
        assert result.exit_code == 0

    def test_creates_active_file_with_draft(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        active_path = tmp_path / ".ftest" / ".active"
        assert active_path.exists()
        assert active_path.read_text().strip() == "draft"

    def test_cli_fails_if_not_a_directory(self, tmp_path: Path) -> None:
        not_a_dir = tmp_path / "somefile.txt"
        not_a_dir.write_text("x")
        result = runner.invoke(app, ["init", str(not_a_dir)])
        assert result.exit_code == 1
        assert "not a directory" in result.output
