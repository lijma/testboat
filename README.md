# testboat

**Manage tests like code — CLI + AI agent skill for the complete testing lifecycle.**

[![PyPI version](https://img.shields.io/pypi/v/testboat?style=for-the-badge)](https://pypi.org/project/testboat/)
[![Python](https://img.shields.io/pypi/pyversions/testboat?style=for-the-badge)](https://pypi.org/project/testboat/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/github/actions/workflow/status/lijma/testboat/release.yml?style=for-the-badge&label=tests)](https://github.com/lijma/testboat/actions)

---

## The Problem

Testing is still managed with scattered spreadsheets, Confluence pages, and tribal knowledge. Test cases drift from requirements, execution results are never recorded, and every sprint the team starts from scratch.

```
WITHOUT testboat

  Strategy lives in a Word doc nobody reads.
  Test cases are in an Excel sheet from 2 years ago.
  "Did we test this?" — nobody knows.
  AI writes automation but nobody tracks coverage.
```

```
WITH testboat

  Strategy, test cases, execution results, bugs — all structured YAML.
  AI generates test cases from requirements, executes automation, files bugs.
  testboat validate checks coverage and exit criteria before any report.
  One source of truth. Git-diffable. Always up to date.
```

---

## How It Works

testboat manages a structured filesystem under `.testboat/` in your workspace:

```
.testboat/
  .active          ← current working version (draft / v1.0 / ...)
  draft/
    strategy.yaml  ← test strategy (scope, risk matrix, exit criteria)
    tags.yaml      ← sprint / type / module tag registry
    cases/         ← TC-001.yaml, TC-002.yaml, ...
    bugs/          ← BUG-001.yaml, BUG-002.yaml, ...
    executions/
      plans/       ← TC-001-plan.yaml (how to execute each TC)
      results/     ← RES-001.yaml (execution results)
      automate/    ← standalone automation sub-projects
    reports/       ← sprint/closure HTML reports
```

**CLI** enforces structure and state machines. **AI agent** generates content, runs automation, and communicates results. Both operate on the same files.

---

## Quick Start

```bash
pip install testboat

# Initialize workspace
testboat init

# Activate agent skill (Claude, Copilot, Cursor, Trae, Kiro, etc.)
testboat enable claude

# Create test strategy
testboat strategy create
# → edit .testboat/draft/strategy.yaml, then:
testboat strategy validate

# Add tags and test cases
testboat tag add sprint v1.0
testboat tag add module auth
testboat case add --title "Login with wrong password returns 401" \
               --sprint v1.0 --type functional --module auth --req-id STORY-001

# Create execution plan and run
testboat plan create TC-001 --type automated --tool pytest
testboat plan register TC-001 .testboat/draft/executions/automate/pytest/tests/test_TC001.py
testboat plan status TC-001 approved

# Record result and file bugs
testboat result record TC-001 pass --type automated
testboat bug add --title "Login 500 error" --tc TC-001 --severity critical --priority P0

# Pre-report validation
testboat validate

# Generate and preview reports
testboat report strategy && testboat report sprint && testboat report closure
testboat preview
```

---

## Commands

| Command | Description |
|---------|-------------|
| `testboat init` | Initialize `.testboat/` workspace |
| `testboat enable <agent>` | Create agent rules + skill files |
| `testboat version create/switch/list` | Manage named versions |
| `testboat strategy create/validate` | Test strategy lifecycle |
| `testboat tag add/list` | Manage sprint / type / module tags |
| `testboat case add/list/show/status/validate` | Test case CRUD + state machine |
| `testboat plan create/register/status` | Execution plan management |
| `testboat result record/list` | Record execution results |
| `testboat matrix show` | Global execution tracking |
| `testboat bug add/list/status` | Bug lifecycle |
| `testboat validate` | Pre-report health check |
| `testboat report strategy/sprint/closure` | Generate HTML reports |
| `testboat preview` | Local report preview server |

## Supported Agents

| Agent | Files created |
|-------|--------------|
| Claude / OpenCode | `.claude/rules/testboat.md` + `.claude/skills/testboat/SKILL.md` |
| GitHub Copilot | `.github/instructions/testboat.instructions.md` |
| Cursor | `.cursor/rules/testboat.md` + `.cursor/skills/testboat/SKILL.md` |
| Trae | `.trae/rules/testboat.md` + `.trae/skills/testboat/SKILL.md` |
| Kiro | `.kiro/steering/testboat.md` |
| OpenClaw | `skills/testboat/SKILL.md` |

---

## Requirements

- Python ≥ 3.11
- Works with any AI agent that supports custom instructions / skills

## License

Apache 2.0
