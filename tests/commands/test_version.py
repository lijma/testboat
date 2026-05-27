"""Unit tests for testboat version command — 100% coverage."""

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from testboat.cli import app
from testboat.commands.active import get_active_version
from testboat.commands.init import init_workspace
from testboat.commands.version import (
    VERSION_META,
    _FRESH_SUBDIRS,
    _draft_path,
    _version_path,
    create_version,
    get_current_active,
    list_versions,
    show_version,
    switch_version,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_draft(root: Path) -> Path:
    """Initialize workspace and put a marker file in cases/."""
    init_workspace(root)
    marker = root / ".testboat" / "draft" / "cases" / "TC-001.yaml"
    marker.write_text("id: TC-001\n")
    return root


# ---------------------------------------------------------------------------
# create_version — fresh (source=None)
# ---------------------------------------------------------------------------


class TestCreateVersionFresh:
    def test_creates_directory(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        vdir = create_version(tmp_path, "v1.0")
        assert vdir.is_dir()

    def test_creates_expected_subdirs(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        vdir = create_version(tmp_path, "v1.0")
        for sub in _FRESH_SUBDIRS:
            assert (vdir / sub).is_dir()

    def test_creates_testboat_yaml(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        vdir = create_version(tmp_path, "v1.0")
        assert (vdir / "testboat.yaml").exists()

    def test_no_tc_files_in_fresh_version(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        vdir = create_version(tmp_path, "v1.0")
        assert list((vdir / "cases").glob("TC-*.yaml")) == []

    def test_meta_base_is_none(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        vdir = create_version(tmp_path, "v1.0")
        meta = yaml.safe_load((vdir / VERSION_META).read_text())
        assert meta["base"] is None
        assert meta["version"] == "v1.0"

    def test_active_switched_to_new_version(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        create_version(tmp_path, "v1.0")
        assert get_active_version(tmp_path) == "v1.0"

    def test_draft_untouched(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        create_version(tmp_path, "v1.0")
        assert (_draft_path(tmp_path) / "cases" / "TC-001.yaml").exists()


# ---------------------------------------------------------------------------
# create_version — from draft (source='draft')
# ---------------------------------------------------------------------------


class TestCreateVersionFromDraft:
    def test_creates_directory(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        vdir = create_version(tmp_path, "v1.0", source="draft")
        assert vdir.is_dir()

    def test_draft_content_copied(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        create_version(tmp_path, "v1.0", source="draft")
        assert (_version_path(tmp_path, "v1.0") / "cases" / "TC-001.yaml").exists()

    def test_draft_untouched_after_create(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        create_version(tmp_path, "v1.0", source="draft")
        assert (_draft_path(tmp_path) / "cases" / "TC-001.yaml").exists()

    def test_meta_base_is_draft(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        vdir = create_version(tmp_path, "v1.0", source="draft")
        meta = yaml.safe_load((vdir / VERSION_META).read_text())
        assert meta["base"] == "draft"

    def test_active_switched(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        create_version(tmp_path, "v1.0", source="draft")
        assert get_active_version(tmp_path) == "v1.0"

    def test_raises_if_draft_missing(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="draft"):
            create_version(tmp_path, "v1.0", source="draft")


# ---------------------------------------------------------------------------
# create_version — from named version (source=<name>)
# ---------------------------------------------------------------------------


class TestCreateVersionFromVersion:
    def test_creates_from_named_version(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        create_version(tmp_path, "v1.0", source="draft")
        extra = _version_path(tmp_path, "v1.0") / "cases" / "TC-002.yaml"
        extra.write_text("id: TC-002\n")
        create_version(tmp_path, "v1.1", source="v1.0")
        assert (_version_path(tmp_path, "v1.1") / "cases" / "TC-002.yaml").exists()

    def test_meta_base_recorded(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        create_version(tmp_path, "v1.0", source="draft")
        vdir = create_version(tmp_path, "v1.1", source="v1.0")
        meta = yaml.safe_load((vdir / VERSION_META).read_text())
        assert meta["base"] == "v1.0"

    def test_active_switched(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        create_version(tmp_path, "v1.0", source="draft")
        create_version(tmp_path, "v1.1", source="v1.0")
        assert get_active_version(tmp_path) == "v1.1"

    def test_raises_if_source_not_found(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        with pytest.raises(FileNotFoundError, match="not found"):
            create_version(tmp_path, "v1.1", source="v9.9")


# ---------------------------------------------------------------------------
# create_version — validation errors
# ---------------------------------------------------------------------------


class TestCreateVersionValidation:
    def test_raises_if_version_exists(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        create_version(tmp_path, "v1.0")
        with pytest.raises(FileExistsError, match="already exists"):
            create_version(tmp_path, "v1.0")

    def test_raises_for_reserved_name_draft(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        with pytest.raises(ValueError, match="Invalid version name"):
            create_version(tmp_path, "draft")

    def test_raises_for_dot_prefix_name(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        with pytest.raises(ValueError, match="Invalid version name"):
            create_version(tmp_path, ".hidden")

    def test_returns_version_path(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        result = create_version(tmp_path, "v1.0")
        assert result == _version_path(tmp_path, "v1.0")

    def test_meta_file_created(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        vdir = create_version(tmp_path, "v1.0")
        assert (vdir / VERSION_META).exists()


# ---------------------------------------------------------------------------
# list_versions
# ---------------------------------------------------------------------------


class TestListVersions:
    def test_empty_when_no_versions(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        assert list_versions(tmp_path) == []

    def test_empty_when_no_testboat_dir(self, tmp_path: Path) -> None:
        assert list_versions(tmp_path) == []

    def test_lists_created_versions(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        create_version(tmp_path, "v1.0", source="draft")
        create_version(tmp_path, "v1.1", source="v1.0")
        versions = list_versions(tmp_path)
        assert len(versions) == 2
        assert versions[0]["version"] == "v1.0"
        assert versions[1]["version"] == "v1.1"

    def test_excludes_draft(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        names = [v["version"] for v in list_versions(tmp_path)]
        assert "draft" not in names

    def test_version_entry_has_cases_count(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        create_version(tmp_path, "v1.0", source="draft")
        v = list_versions(tmp_path)[0]
        assert v["cases"] == 1

    def test_version_entry_has_base(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        create_version(tmp_path, "v1.0", source="draft")
        create_version(tmp_path, "v1.1", source="v1.0")
        v11 = next(v for v in list_versions(tmp_path) if v["version"] == "v1.1")
        assert v11["base"] == "v1.0"


# ---------------------------------------------------------------------------
# show_version
# ---------------------------------------------------------------------------


class TestShowVersion:
    def test_returns_version_info(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        create_version(tmp_path, "v1.0", source="draft")
        info = show_version(tmp_path, "v1.0")
        assert info["version"] == "v1.0"
        assert info["cases"] == 1

    def test_raises_if_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            show_version(tmp_path, "v9.9")

    def test_results_count(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        create_version(tmp_path, "v1.0")
        info = show_version(tmp_path, "v1.0")
        assert info["results"] == 0

    def test_version_without_meta(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        vdir = create_version(tmp_path, "v1.0")
        (vdir / VERSION_META).unlink()
        info = show_version(tmp_path, "v1.0")
        assert info["base"] is None


# ---------------------------------------------------------------------------
# switch_version / get_current_active
# ---------------------------------------------------------------------------


class TestSwitchVersion:
    def test_switch_to_existing_version(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        create_version(tmp_path, "v1.0")
        switch_version(tmp_path, "v1.0")
        assert get_active_version(tmp_path) == "v1.0"

    def test_switch_returns_version_name(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        create_version(tmp_path, "v1.0")
        assert switch_version(tmp_path, "v1.0") == "v1.0"

    def test_switch_to_draft(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        switch_version(tmp_path, "draft")
        assert get_active_version(tmp_path) == "draft"

    def test_switch_raises_if_not_found(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        with pytest.raises(FileNotFoundError):
            switch_version(tmp_path, "v9.9")

    def test_get_current_active_default(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        assert get_current_active(tmp_path) == "draft"

    def test_get_current_active_after_switch(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        create_version(tmp_path, "v1.0")
        switch_version(tmp_path, "v1.0")
        assert get_current_active(tmp_path) == "v1.0"


# ---------------------------------------------------------------------------
# CLI — new "testboat version XXX [source]" syntax
# ---------------------------------------------------------------------------


class TestVersionCli:
    def test_fresh_version_created(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        result = runner.invoke(app, ["version", "v1.0", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "fresh" in result.output
        assert "v1.0" in result.output

    def test_fresh_switches_active(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        runner.invoke(app, ["version", "v1.0", "--workspace", str(tmp_path)])
        assert get_active_version(tmp_path) == "v1.0"

    def test_from_draft_syntax(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        result = runner.invoke(app, ["version", "v1.0", "draft",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "draft" in result.output

    def test_from_draft_copies_content(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        runner.invoke(app, ["version", "v1.0", "draft", "--workspace", str(tmp_path)])
        assert (_version_path(tmp_path, "v1.0") / "cases" / "TC-001.yaml").exists()

    def test_from_named_version_syntax(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        runner.invoke(app, ["version", "v1.0", "draft", "--workspace", str(tmp_path)])
        result = runner.invoke(app, ["version", "v2.0", "v1.0",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "v1.0" in result.output

    def test_duplicate_version_exits_one(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        runner.invoke(app, ["version", "v1.0", "--workspace", str(tmp_path)])
        result = runner.invoke(app, ["version", "v1.0", "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_invalid_name_exits_one(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        result = runner.invoke(app, ["version", "draft", "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_source_not_found_exits_one(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        result = runner.invoke(app, ["version", "v1.0", "v9.9",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_list_empty(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        result = runner.invoke(app, ["version", "list", str(tmp_path)])
        assert result.exit_code == 0
        assert "No named versions" in result.output

    def test_list_shows_active_marker(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        create_version(tmp_path, "v1.0")
        result = runner.invoke(app, ["version", "list", str(tmp_path)])
        assert "◀ active" in result.output

    def test_list_shows_fresh_label(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        create_version(tmp_path, "v1.0")
        result = runner.invoke(app, ["version", "list", str(tmp_path)])
        assert "(fresh)" in result.output

    def test_switch_sets_active(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        create_version(tmp_path, "v1.0")
        switch_version(tmp_path, "draft")
        result = runner.invoke(app, ["version", "switch", "v1.0",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert get_active_version(tmp_path) == "v1.0"

    def test_switch_to_draft(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        create_version(tmp_path, "v1.0")
        runner.invoke(app, ["version", "switch", "draft", "--workspace", str(tmp_path)])
        assert get_active_version(tmp_path) == "draft"

    def test_switch_not_found_exits_one(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        result = runner.invoke(app, ["version", "switch", "v9.9",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_active_shows_current(self, tmp_path: Path) -> None:
        _make_draft(tmp_path)
        result = runner.invoke(app, ["version", "active", str(tmp_path)])
        assert result.exit_code == 0
        assert "draft" in result.output

    def test_show_version(self, tmp_path: Path) -> None:
        init_workspace(tmp_path)
        create_version(tmp_path, "v1.0")
        result = runner.invoke(app, ["version", "show", "v1.0",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "v1.0" in result.output
        assert "Cases" in result.output

    def test_show_not_found_exits_one(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["version", "show", "v9.9",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_option_arg_not_treated_as_version(self, tmp_path: Path) -> None:
        # passing '--help' should show help, not crash or create a version
        result = runner.invoke(app, ["version", "--help"])
        assert result.exit_code == 0

    def test_create_without_ctx_obj_exits_one(self, tmp_path: Path) -> None:
        # Invoke the hidden _create command directly without ctx.obj set
        result = runner.invoke(app, ["version", "_create",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 1
        assert "no version name" in result.output

    def test_version_group_returns_none_for_option_like_name(self) -> None:
        import click
        from testboat.cli import _VersionGroup
        group = _VersionGroup(name="version")
        ctx = click.Context(group)
        assert group.get_command(ctx, "--unknown-flag") is None
