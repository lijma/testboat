# ftest

**Manage tests like code — CLI + AI agent skill for the complete testing lifecycle.**

[![PyPI version](https://img.shields.io/pypi/v/ftest?style=for-the-badge)](https://pypi.org/project/ftest/)
[![Python](https://img.shields.io/pypi/pyversions/ftest?style=for-the-badge)](https://pypi.org/project/ftest/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/github/actions/workflow/status/lijma/ftest/release.yml?style=for-the-badge&label=tests)](https://github.com/lijma/ftest/actions)

---

## The Problem

Testing is still managed with scattered spreadsheets, Confluence pages, and tribal knowledge. Test cases drift from requirements, execution results are never recorded, and every sprint the team starts from scratch.

```
WITHOUT ftest

  Strategy lives in a Word doc nobody reads.
  Test cases are in an Excel sheet from 2 years ago.
  "Did we test this?" — nobody knows.
  AI writes automation but nobody tracks coverage.
```

```
WITH ftest

  Strategy, test cases, execution results, bugs — all structured YAML.
  AI generates test cases from requirements, executes automation, files bugs.
  ftest validate checks coverage and exit criteria before any report.
  One source of truth. Git-diffable. Always up to date.
```

---

## How It Works

ftest manages a structured filesystem under `.ftest/` in your workspace:

```
.ftest/
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
pip install ftest

# Initialize workspace
ftest init

# Activate agent skill (Claude, Copilot, Cursor, Trae, Kiro, etc.)
ftest enable claude

# Create test strategy
ftest strategy create
# → edit .ftest/draft/strategy.yaml, then:
ftest strategy validate

# Add tags and test cases
ftest tag add sprint v1.0
ftest tag add module auth
ftest case add --title "Login with wrong password returns 401" \
               --sprint v1.0 --type functional --module auth --req-id STORY-001

# Create execution plan and run
ftest plan create TC-001 --type automated --tool pytest
ftest plan register TC-001 .ftest/draft/executions/automate/pytest/tests/test_TC001.py
ftest plan status TC-001 approved

# Record result and file bugs
ftest result record TC-001 pass --type automated
ftest bug add --title "Login 500 error" --tc TC-001 --severity critical --priority P0

# Pre-report validation
ftest validate

# Generate and preview reports
ftest report strategy && ftest report sprint && ftest report closure
ftest preview
```

---

## Commands

| Command | Description |
|---------|-------------|
| `ftest init` | Initialize `.ftest/` workspace |
| `ftest enable <agent>` | Create agent rules + skill files |
| `ftest version create/switch/list` | Manage named versions |
| `ftest strategy create/validate` | Test strategy lifecycle |
| `ftest tag add/list` | Manage sprint / type / module tags |
| `ftest case add/list/show/status/validate` | Test case CRUD + state machine |
| `ftest plan create/register/status` | Execution plan management |
| `ftest result record/list` | Record execution results |
| `ftest matrix show` | Global execution tracking |
| `ftest bug add/list/status` | Bug lifecycle |
| `ftest validate` | Pre-report health check |
| `ftest report strategy/sprint/closure` | Generate HTML reports |
| `ftest preview` | Local report preview server |

## Supported Agents

| Agent | Files created |
|-------|--------------|
| Claude / OpenCode | `.claude/rules/ftest.md` + `.claude/skills/ftest/SKILL.md` |
| GitHub Copilot | `.github/instructions/ftest.instructions.md` |
| Cursor | `.cursor/rules/ftest.md` + `.cursor/skills/ftest/SKILL.md` |
| Trae | `.trae/rules/ftest.md` + `.trae/skills/ftest/SKILL.md` |
| Kiro | `.kiro/steering/ftest.md` |
| OpenClaw | `skills/ftest/SKILL.md` |

---

## Requirements

- Python ≥ 3.11
- Works with any AI agent that supports custom instructions / skills

## License

Apache 2.0
