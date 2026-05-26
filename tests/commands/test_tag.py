"""Unit tests for testboat tag command — 100% coverage."""

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from testboat.cli import app
from testboat.commands.tag import (
    DEFAULT_TAGS,
    TAG_KINDS,
    _tags_path,
    add_tag,
    init_tags,
    list_tags,
    tag_exists,
)

runner = CliRunner()


class TestAddTag:
    def test_adds_new_value(self, tmp_path: Path) -> None:
        assert add_tag(tmp_path, "sprint", "v1.0.0") is True
        assert tag_exists(tmp_path, "sprint", "v1.0.0")

    def test_returns_false_if_already_exists(self, tmp_path: Path) -> None:
        add_tag(tmp_path, "sprint", "v1.0.0")
        assert add_tag(tmp_path, "sprint", "v1.0.0") is False

    def test_raises_for_unknown_kind(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Unknown tag kind"):
            add_tag(tmp_path, "unknown", "value")

    def test_creates_tags_file(self, tmp_path: Path) -> None:
        add_tag(tmp_path, "module", "auth")
        assert _tags_path(tmp_path).exists()

    def test_persists_across_calls(self, tmp_path: Path) -> None:
        add_tag(tmp_path, "module", "auth")
        add_tag(tmp_path, "module", "payment")
        data = list_tags(tmp_path)
        assert "auth" in data["module"]
        assert "payment" in data["module"]


class TestListTags:
    def test_returns_all_kinds(self, tmp_path: Path) -> None:
        tags = list_tags(tmp_path)
        for kind in TAG_KINDS:
            assert kind in tags

    def test_default_type_tags_present(self, tmp_path: Path) -> None:
        tags = list_tags(tmp_path)
        for t in DEFAULT_TAGS["type"]:
            assert t in tags["type"]

    def test_empty_sprint_by_default(self, tmp_path: Path) -> None:
        tags = list_tags(tmp_path)
        assert tags["sprint"] == []


class TestTagExists:
    def test_returns_true_for_existing(self, tmp_path: Path) -> None:
        add_tag(tmp_path, "sprint", "v2.0")
        assert tag_exists(tmp_path, "sprint", "v2.0") is True

    def test_returns_false_for_missing(self, tmp_path: Path) -> None:
        assert tag_exists(tmp_path, "sprint", "v9.9") is False

    def test_returns_false_for_unknown_kind(self, tmp_path: Path) -> None:
        assert tag_exists(tmp_path, "unknown", "x") is False


class TestInitTags:
    def test_creates_tags_file(self, tmp_path: Path) -> None:
        init_tags(tmp_path)
        assert _tags_path(tmp_path).exists()

    def test_idempotent(self, tmp_path: Path) -> None:
        init_tags(tmp_path)
        add_tag(tmp_path, "sprint", "v1.0.0")
        init_tags(tmp_path)  # should not overwrite
        assert tag_exists(tmp_path, "sprint", "v1.0.0")


class TestTagCli:
    def test_add_sprint_tag(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["tag", "add", "sprint", "v1.0.0", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "Added" in result.output

    def test_add_duplicate_tag(self, tmp_path: Path) -> None:
        runner.invoke(app, ["tag", "add", "sprint", "v1.0.0", "--workspace", str(tmp_path)])
        result = runner.invoke(app, ["tag", "add", "sprint", "v1.0.0", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "already exists" in result.output

    def test_add_unknown_kind_exits_one(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["tag", "add", "unknown", "val", "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_list_shows_all_kinds(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["tag", "list", str(tmp_path)])
        assert result.exit_code == 0
        for kind in TAG_KINDS:
            assert kind in result.output

    def test_list_shows_added_value(self, tmp_path: Path) -> None:
        runner.invoke(app, ["tag", "add", "module", "auth", "--workspace", str(tmp_path)])
        result = runner.invoke(app, ["tag", "list", str(tmp_path)])
        assert "auth" in result.output
