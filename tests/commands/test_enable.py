"""Unit tests for ftest enable command — 100% coverage."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from ftest.cli import app
from ftest.commands.enable import (
    AGENTS,
    COPILOT_CONTENT,
    KIRO_CONTENT,
    RULES_CONTENT,
    SKILL_CONTENT,
    _CONTENT_MAP,
    _resolve,
    enable_agent,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# _resolve() — alias resolution
# ---------------------------------------------------------------------------


class TestResolve:
    def test_non_alias_returns_self(self) -> None:
        name, config = _resolve("claude")
        assert name == "claude"
        assert "rules_path" in config

    def test_alias_resolves_to_target(self) -> None:
        name, config = _resolve("opencode")
        assert name == "claude"
        assert "rules_path" in config


# ---------------------------------------------------------------------------
# enable_agent() — file creation per agent
# ---------------------------------------------------------------------------


class TestEnableAgentFiles:
    # claude: rules + skill
    def test_claude_creates_rules_file(self, tmp_path: Path) -> None:
        enable_agent(tmp_path, "claude")
        assert (tmp_path / ".claude/rules/ftest.md").exists()

    def test_claude_rules_content(self, tmp_path: Path) -> None:
        enable_agent(tmp_path, "claude")
        assert (tmp_path / ".claude/rules/ftest.md").read_text() == RULES_CONTENT

    def test_claude_creates_skill_file(self, tmp_path: Path) -> None:
        enable_agent(tmp_path, "claude")
        assert (tmp_path / ".claude/skills/ftest/SKILL.md").exists()

    def test_claude_skill_content(self, tmp_path: Path) -> None:
        enable_agent(tmp_path, "claude")
        assert (tmp_path / ".claude/skills/ftest/SKILL.md").read_text() == SKILL_CONTENT

    def test_claude_returns_two_paths(self, tmp_path: Path) -> None:
        assert len(enable_agent(tmp_path, "claude")) == 2

    # opencode: alias for claude
    def test_opencode_creates_same_files_as_claude(self, tmp_path: Path) -> None:
        created = enable_agent(tmp_path, "opencode")
        assert (tmp_path / ".claude/rules/ftest.md").exists()
        assert (tmp_path / ".claude/skills/ftest/SKILL.md").exists()
        assert len(created) == 2

    # copilot: instructions only (applyTo: '**')
    def test_copilot_creates_instructions_file(self, tmp_path: Path) -> None:
        enable_agent(tmp_path, "copilot")
        assert (tmp_path / ".github/instructions/ftest.instructions.md").exists()

    def test_copilot_instructions_has_apply_to(self, tmp_path: Path) -> None:
        enable_agent(tmp_path, "copilot")
        content = (tmp_path / ".github/instructions/ftest.instructions.md").read_text()
        assert "applyTo: '**'" in content
        assert content == COPILOT_CONTENT

    def test_copilot_returns_one_path(self, tmp_path: Path) -> None:
        assert len(enable_agent(tmp_path, "copilot")) == 1

    # cursor: rules + skill
    def test_cursor_creates_rules_file(self, tmp_path: Path) -> None:
        enable_agent(tmp_path, "cursor")
        assert (tmp_path / ".cursor/rules/ftest.md").exists()

    def test_cursor_creates_skill_file(self, tmp_path: Path) -> None:
        enable_agent(tmp_path, "cursor")
        assert (tmp_path / ".cursor/skills/ftest/SKILL.md").exists()

    def test_cursor_returns_two_paths(self, tmp_path: Path) -> None:
        assert len(enable_agent(tmp_path, "cursor")) == 2

    # trae: rules + skill
    def test_trae_creates_rules_file(self, tmp_path: Path) -> None:
        enable_agent(tmp_path, "trae")
        assert (tmp_path / ".trae/rules/ftest.md").exists()

    def test_trae_creates_skill_file(self, tmp_path: Path) -> None:
        enable_agent(tmp_path, "trae")
        assert (tmp_path / ".trae/skills/ftest/SKILL.md").exists()

    def test_trae_returns_two_paths(self, tmp_path: Path) -> None:
        assert len(enable_agent(tmp_path, "trae")) == 2

    # kiro: steering only (inclusion: always)
    def test_kiro_creates_steering_file(self, tmp_path: Path) -> None:
        enable_agent(tmp_path, "kiro")
        assert (tmp_path / ".kiro/steering/ftest.md").exists()

    def test_kiro_steering_has_inclusion_always(self, tmp_path: Path) -> None:
        enable_agent(tmp_path, "kiro")
        content = (tmp_path / ".kiro/steering/ftest.md").read_text()
        assert "inclusion: always" in content
        assert content == KIRO_CONTENT

    def test_kiro_returns_one_path(self, tmp_path: Path) -> None:
        assert len(enable_agent(tmp_path, "kiro")) == 1

    # openclaw: skill only
    def test_openclaw_creates_skill_file(self, tmp_path: Path) -> None:
        enable_agent(tmp_path, "openclaw")
        assert (tmp_path / "skills/ftest/SKILL.md").exists()

    def test_openclaw_returns_one_path(self, tmp_path: Path) -> None:
        assert len(enable_agent(tmp_path, "openclaw")) == 1

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        enable_agent(tmp_path, "claude")
        assert (tmp_path / ".claude/rules").is_dir()
        assert (tmp_path / ".claude/skills/ftest").is_dir()


# ---------------------------------------------------------------------------
# enable_agent() — idempotent behaviour
# ---------------------------------------------------------------------------


class TestEnableAgentIdempotent:
    def test_second_run_does_not_raise(self, tmp_path: Path) -> None:
        enable_agent(tmp_path, "claude")
        enable_agent(tmp_path, "claude")  # must not raise

    def test_second_run_overwrites_rules(self, tmp_path: Path) -> None:
        rules = tmp_path / ".claude/rules/ftest.md"
        enable_agent(tmp_path, "claude")
        rules.write_text("old content", encoding="utf-8")
        enable_agent(tmp_path, "claude")
        assert rules.read_text() == RULES_CONTENT

    def test_second_run_overwrites_skill(self, tmp_path: Path) -> None:
        skill = tmp_path / ".claude/skills/ftest/SKILL.md"
        enable_agent(tmp_path, "claude")
        skill.write_text("old content", encoding="utf-8")
        enable_agent(tmp_path, "claude")
        assert skill.read_text() == SKILL_CONTENT

    def test_agent_name_case_insensitive(self, tmp_path: Path) -> None:
        assert len(enable_agent(tmp_path, "Claude")) == 2


# ---------------------------------------------------------------------------
# enable_agent() — error handling
# ---------------------------------------------------------------------------


class TestEnableAgentErrors:
    def test_raises_value_error_for_unknown_agent(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Unsupported agent"):
            enable_agent(tmp_path, "unknown")

    def test_error_message_lists_supported_agents(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="claude"):
            enable_agent(tmp_path, "ghost")


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


class TestEnableCli:
    def test_cli_enable_claude_exit_zero(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["enable", "claude", "--workspace", str(tmp_path)])
        assert result.exit_code == 0

    def test_cli_enable_claude_shows_both_files(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["enable", "claude", "--workspace", str(tmp_path)])
        assert ".claude/rules/ftest.md" in result.output
        assert ".claude/skills/ftest/SKILL.md" in result.output

    def test_cli_enable_opencode_shows_alias(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["enable", "opencode", "--workspace", str(tmp_path)])
        assert "claude" in result.output

    def test_cli_enable_copilot(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["enable", "copilot", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "ftest.instructions.md" in result.output

    def test_cli_enable_kiro(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["enable", "kiro", "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert ".kiro/steering/ftest.md" in result.output

    def test_cli_idempotent_second_run(self, tmp_path: Path) -> None:
        runner.invoke(app, ["enable", "claude", "--workspace", str(tmp_path)])
        result = runner.invoke(app, ["enable", "claude", "--workspace", str(tmp_path)])
        assert result.exit_code == 0

    def test_cli_enable_unknown_agent_exits_one(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["enable", "ghost", "--workspace", str(tmp_path)])
        assert result.exit_code == 1
        assert "Unsupported agent" in result.output

    def test_cli_list_shows_all_agents(self) -> None:
        result = runner.invoke(app, ["enable", "list"])
        assert result.exit_code == 0
        for name in AGENTS:
            assert name in result.output

    def test_cli_list_shows_alias(self) -> None:
        result = runner.invoke(app, ["enable", "list"])
        assert "alias" in result.output
