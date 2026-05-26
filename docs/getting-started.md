# Getting Started

## Install

```bash
pip install testboat
```

## Initialize Workspace

```bash
cd your-project
testboat init
```

Creates `.testboat/draft/` with the standard directory structure and sets the active version to `draft`.

## Enable Your AI Agent

```bash
testboat enable claude      # Claude Code
testboat enable copilot     # GitHub Copilot
testboat enable cursor      # Cursor
testboat enable kiro        # Kiro
testboat enable list        # see all supported agents
```

This creates agent-specific instruction files so your AI automatically follows the testboat workflow.

## Create a Test Strategy

```bash
testboat strategy create
```

Edit `.testboat/draft/strategy.yaml` — fill in scope, risk matrix, entry/exit criteria — then validate:

```bash
testboat strategy validate
```

## Add Test Cases

```bash
# Register tags first
testboat tag add sprint v1.0
testboat tag add type functional
testboat tag add module auth

# Create a test case (AI fills in the steps)
testboat case add --title "Login with wrong password returns 401" \
               --sprint v1.0 --type functional --module auth --req-id STORY-001
```

Then ask your AI agent to fill in `steps`, `preconditions`, and `expected_result` in the generated YAML file.

## Execute and Record Results

```bash
# Create execution plan
testboat plan create TC-001 --type automated --tool pytest

# Register automation script
testboat plan register TC-001 .testboat/draft/executions/automate/pytest/tests/test_TC001.py
testboat plan status TC-001 approved

# Record result (AI runs the script and records)
testboat result record TC-001 pass --type automated --by "AI"
```

## Validate Before Reporting

```bash
testboat validate
```

Checks: format integrity · requirements coverage · execution completeness · exit criteria.

## Generate Reports

```bash
testboat report strategy   # test strategy HTML
testboat report sprint     # sprint test report (cases + results + bugs)
testboat report closure    # closure report with sign-off status
testboat preview           # open in browser on a random local port
```

## Manage Versions

```bash
testboat version create v1.0          # snapshot draft as v1.0
testboat version create v1.1 v1.0     # create v1.1 based on v1.0
testboat version switch v1.0          # all commands now operate on v1.0
testboat version active               # show current active version
testboat version list                 # list all versions
```
