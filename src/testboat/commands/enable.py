"""testboat enable — create agent rules + skill files for testboat in the workspace."""

from pathlib import Path

# ---------------------------------------------------------------------------
# File contents
# ---------------------------------------------------------------------------

# Rules body: always-loaded every session, kept short (< 200 tokens).
# Used by: claude, cursor, trae (plain markdown, no frontmatter).
RULES_CONTENT = """\
# testboat

This workspace uses testboat to manage tests like code.

Test artifacts live in `.testboat/draft/`:
- `strategy/`   — test strategy documents
- `cases/`      — TC-xxx.yaml test case files
- `executions/` — execution results (Playwright / JMeter / ZAP)
- `bugs/`       — bug records
- `reports/`    — generated reports

When doing test-related work:
- Check `.testboat/draft/` before creating new test artifacts
- Use `testboat` CLI to manage lifecycle (`testboat --help`)
- File naming: `TC-001.yaml`, `BUG-001.yaml`, `YYYY-MM-DD-suite.yaml`
"""

# Copilot instructions: always-on, requires applyTo frontmatter.
COPILOT_CONTENT = """\
---
name: 'testboat'
description: 'This workspace uses testboat CLI. Test artifacts live in .testboat/draft/ (strategy, cases, executions, bugs, reports). Use testboat commands when doing test-related work.'
applyTo: '**'
---

# testboat

This workspace uses testboat to manage tests like code.

Test artifacts live in `.testboat/draft/`:
- `strategy/`   — test strategy documents
- `cases/`      — TC-xxx.yaml test case files
- `executions/` — execution results (Playwright / JMeter / ZAP)
- `bugs/`       — bug records
- `reports/`    — generated reports

When doing test-related work:
- Check `.testboat/draft/` before creating new test artifacts
- Use `testboat` CLI to manage lifecycle (`testboat --help`)
- File naming: `TC-001.yaml`, `BUG-001.yaml`, `YYYY-MM-DD-suite.yaml`
"""

# Kiro steering: frontmatter controls inclusion mode.
KIRO_CONTENT = """\
---
inclusion: always
---

# testboat

This workspace uses testboat to manage tests like code.

Test artifacts live in `.testboat/draft/`:
- `strategy/`   — test strategy documents
- `cases/`      — TC-xxx.yaml test case files
- `executions/` — execution results (Playwright / JMeter / ZAP)
- `bugs/`       — bug records
- `reports/`    — generated reports

When doing test-related work:
- Check `.testboat/draft/` before creating new test artifacts
- Use `testboat` CLI to manage lifecycle (`testboat --help`)
- File naming: `TC-001.yaml`, `BUG-001.yaml`, `YYYY-MM-DD-suite.yaml`
"""

# Skill body: detailed workflow, loaded on-demand.
# Used by: claude, cursor, trae, openclaw.
SKILL_CONTENT = """\
---
name: testboat
description: Test management workflow. Use when creating test strategy, writing test cases, running automation (Playwright/JMeter/ZAP), or generating sprint/closure reports. Manages .testboat/draft/ filesystem.
---

# testboat — Manage Tests Like Code

The `.testboat/` directory is the test artifact filesystem for this project.
AI and CLI are both clients of this filesystem — **files are the single source of truth**.

## Directory Structure

```
.testboat/draft/
  strategy/     ← test strategy documents
  cases/        ← TC-xxx.yaml test case files
  executions/   ← execution results (Playwright / JMeter / ZAP)
  bugs/         ← bug records
  reports/      ← generated reports
  testboat.yaml    ← project config
```

## File Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Test case | `TC-{seq:03d}.yaml` | `TC-001.yaml` |
| Execution result | `{YYYY-MM-DD}-{suite}.yaml` | `2026-05-26-smoke.yaml` |
| Bug | `BUG-{seq:03d}.yaml` | `BUG-001.yaml` |

## Event-Driven Workflow

Any user input during the testing lifecycle triggers this loop:

```
User Input → Classify → Update Artifact → testboat validate → Regress if needed → Communicate
```

| Event | Artifact to update | Extra action |
|-------|-------------------|--------------|
| Comment on strategy/TC | Edit YAML, re-validate | Re-run if TC was already executed |
| Manual result overrides automation | `testboat result record --type manual` | File bug if automation is wrong |
| User sends test results (batch) | `testboat result record` × N | File bugs for all fails |
| New requirement | strategy.yaml + new TCs | Full mini-SOP, then regression |
| Bug fixed by dev | Re-run affected TCs | `testboat bug status → verified → closed` |

**Always**: confirm understanding before acting · update only what's affected · run `testboat validate` after.

---

## Active Version

**ALWAYS check the active version before reading or writing test artifacts.**

```bash
testboat version active   # see which version is active
```

The active version is stored in `.testboat/.active`. All commands (case, tag, strategy, bug, plan, result, report) operate on `.testboat/<active-version>/`. Default is `draft`.

If you need to work in a specific version:
```bash
testboat version switch v1.0   # now all commands operate on .testboat/v1.0/
testboat version switch draft  # back to working area
```

**Before creating or modifying any artifact, confirm you are in the correct version.**

---

## AI Workflows

### 1. Update Test Strategy
Trigger: user asks to update strategy, or new requirements added.

Steps:
1. Understand current release scope — read requirements from wherever they live
   (docs, tickets, PRD, requirements tracking tools, or user input)
2. Read `.testboat/draft/strategy/strategy.yaml`
3. Update fields based on requirements:
   - `scope.in_scope` / `out_scope` — align with current release scope
   - `risk_matrix` — add/adjust entries for new high-risk areas
   - `entry_criteria` / `exit_criteria` — reflect current acceptance bar
4. Write updated YAML back to `strategy/strategy.yaml`
5. Run `testboat strategy validate` — must pass before proceeding

### 2. Test Case SOP
Trigger: strategy is approved, user asks to create / update test cases.

Steps:
1. Read `strategy/strategy.yaml` — scope and risk_matrix drive what to cover and priority
2. Run `testboat tag list` — check available sprint / type / module tags; add missing ones with `testboat tag add`
3. For each scenario to cover, run:
   `testboat case add --title "..." --sprint <s> --type <t> --module <m> --req-id <id>`
   This creates TC-xxx.yaml with metadata only (steps are empty — AI fills them next)
4. For each created TC, fill in `preconditions`, `steps`, and `expected_result` directly into the YAML file
5. Run `testboat case validate all` — all cases must pass before marking ready
6. Run `testboat case status TC-xxx ready` for each validated case

AI review (between step 4 and 5):
1. Run `testboat case list` (with filters if needed: --sprint / --type / --module) — get the full list to understand scope before reviewing
2. For each TC in the list, read the YAML file and check: edge case coverage, clear action/expected pairs, no duplicate cases
3. Update steps where gaps are found
4. Then proceed to `testboat case validate all`

### 3. Execution Planning + Automation
Trigger: test cases are ready, user asks to plan and execute tests.

Steps:
1. Read `strategy/strategy.yaml` and `cases/TC-*.yaml`
2. For each TC, run `testboat plan create TC-xxx --type <manual|automated|both>`
   - Tool defaults by TC type: functional/regression/smoke→playwright, performance→jmeter, security→zap, mobile→maestro
3. For automated TCs, write the automation script into the independent sub-project:
   - Scripts live in `.testboat/draft/automate/<platform>/` — **standalone sub-projects, no source code imports**
   - playwright → `.testboat/draft/automate/playwright/tests/TC-xxx.spec.ts`
   - pytest     → `.testboat/draft/automate/pytest/tests/test_TCxxx.py`
   - jmeter     → `.testboat/draft/automate/jmeter/TC-xxx/test.jmx`
   - maestro    → `.testboat/draft/automate/maestro/TC-xxx/flow.yaml`
4. Run `testboat plan register TC-xxx .testboat/draft/automate/<platform>/tests/<script>`
   → Links the script to the plan; tool is auto-detected from file extension
5. Run `testboat plan status TC-xxx approved`
6. Execute:
   - **Manual**: guide user through TC steps → `testboat result record TC-xxx pass|fail --type manual`
   - **Automated**: read `show_plan(TC-xxx).automation_path` → run script via shell → `testboat result record TC-xxx pass|fail --type automated --by "AI"`
7. `testboat matrix show` to check overall progress; communicate results to user

### 4. Bug Management
Trigger: a TC fails, or user reports a defect.

Steps:
1. Run `testboat bug add --title "..." --tc TC-xxx --result RES-xxx --severity <sev> --priority <pri>`
   - Severity (technical impact): critical / major / minor / cosmetic
   - Priority (business urgency): P0 / P1 / P2 / P3
2. Fill in `steps_to_reproduce`, `expected`, `actual` in BUG-xxx.yaml
3. Communicate bug to user: confirm priority and assignee
4. After fix: re-run TC → `testboat result record TC-xxx pass`
   → `testboat bug status BUG-xxx verified`
   → `testboat bug status BUG-xxx closed`
5. `testboat bug list --status new` to check open bugs at any time

Bug status machine:
  new → triaged → in-progress → fixed → pending-retest → verified → closed
                       ↓                                    ↑
                deferred / wont-fix           in-progress (retest fail)

**After any bug fix: always run Workflow 5 (Regression Testing Loop).**

### 5. Regression Testing Loop (MANDATORY after any change)
Trigger: **ALWAYS run after**: new requirement implemented, bug fixed, code refactored, or any file in the project changed.

This closes the loop. Never skip this step.

Steps:
1. Identify affected scope:
   - New requirement → `testboat case list --sprint <sprint> --module <affected-module>`
   - Bug fix → read BUG-xxx.yaml to get `tc_id` and `tags.module`; list all TCs in that module
   - Code change → identify which modules changed; list TCs for those modules
2. Re-run affected automation scripts:
   - For each affected TC that has an approved plan: read `plan.automation_path` → run script → `testboat result record TC-xxx pass|fail --type automated --by "AI"`
   - For manual TCs: notify user to retest, record result after confirmation
3. Check for regressions:
   - `testboat matrix show` — compare latest_status with previous; flag any new failures
   - If new failures found: create bug reports → go to Workflow 4 (Bug Management)
4. If fixing a bug:
   - TC that found the bug must pass before marking bug verified
   - `testboat bug status BUG-xxx pending-retest`
   - Re-run TC → if pass: `testboat bug status BUG-xxx verified` → `testboat bug status BUG-xxx closed`
   - If still fail: `testboat bug status BUG-xxx in-progress`, communicate to user
5. Communicate regression summary to user:
   - How many TCs re-run, how many pass/fail
   - Any new bugs opened
   - Overall matrix status

### 6. Generate Report
Trigger: sprint ends, `testboat validate` passes, user asks for report.

Steps:
1. Run `testboat validate` — must pass (or user accepts known issues)
2. Write executive summary text (AI narrative: overall status, key risks, recommendations)
3. Generate reports:
   - `testboat report strategy` → strategy.html
   - `testboat report sprint` → sprint-{release}.html
   - `testboat report closure --summary "<AI-written summary>"` → closure-{release}.html
4. Preview: `testboat preview` → opens browser on random local port
5. Export PDF: `testboat preview --pdf .testboat/draft/reports/closure-{release}.html`

AI narrative for closure summary should include:
- Overall pass/fail assessment
- Key risks identified during testing
- Notable bugs and their impact
- Recommendation (ready for release / not ready)

## CLI Commands

```bash
testboat init                              # initialize .testboat/ workspace (sets active=draft)
testboat enable <agent>                    # create agent rules + skill
testboat version active                    # show currently active version
testboat version switch <v>               # switch active version (all commands operate here)
testboat version list                     # list all versions (shows active marker ◀)
testboat strategy create / validate        # strategy template + schema check
testboat case add/list/show/status/validate  # test case lifecycle
testboat tag add/list                      # tag registry
testboat plan create/list/show/status      # execution plan CRUD
testboat plan register TC-xxx <script>     # link automation script to plan
testboat result record/list/show           # execution result recording
testboat matrix show [TC-xxx]              # global execution tracking table
testboat bug add/list/show/status          # bug lifecycle (new→triaged→in-progress→fixed→pending-retest→verified→closed)
testboat report strategy/sprint/closure    # generate HTML reports
testboat preview [--pdf <html>]           # serve locally or export PDF
```
"""

# ---------------------------------------------------------------------------
# Agent configuration
# ---------------------------------------------------------------------------

# Each agent entry may have:
#   rules_path        → always-loaded rules file (claude, cursor, trae)
#   instructions_path → always-on instructions file (copilot)
#   steering_path     → always-loaded steering file (kiro)
#   skill_path        → on-demand skill file (claude, cursor, trae, openclaw)
#   alias             → delegate to another agent key

AGENTS: dict[str, dict] = {
    "claude": {
        "rules_path": ".claude/rules/testboat.md",
        "skill_path": ".claude/skills/testboat/SKILL.md",
    },
    "opencode": {"alias": "claude"},
    "copilot": {
        "instructions_path": ".github/instructions/testboat.instructions.md",
    },
    "cursor": {
        "rules_path": ".cursor/rules/testboat.md",
        "skill_path": ".cursor/skills/testboat/SKILL.md",
    },
    "trae": {
        "rules_path": ".trae/rules/testboat.md",
        "skill_path": ".trae/skills/testboat/SKILL.md",
    },
    "kiro": {
        "steering_path": ".kiro/steering/testboat.md",
    },
    "openclaw": {
        "skill_path": "skills/testboat/SKILL.md",
    },
}

_CONTENT_MAP = {
    "rules_path": RULES_CONTENT,
    "instructions_path": COPILOT_CONTENT,
    "steering_path": KIRO_CONTENT,
    "skill_path": SKILL_CONTENT,
}


def _resolve(agent: str) -> tuple[str, dict]:
    """Return (canonical_name, config), resolving aliases."""
    config = AGENTS[agent]
    if "alias" in config:
        canonical = config["alias"]
        return canonical, AGENTS[canonical]
    return agent, config


def enable_agent(workspace: Path, agent: str) -> list[Path]:
    """Create (or overwrite) testboat rules + skill files for *agent* under *workspace*.

    Idempotent: safe to run multiple times.
    Returns list of written file paths.
    Raises ValueError for unsupported agents.
    """
    agent = agent.lower()
    if agent not in AGENTS:
        supported = ", ".join(sorted(AGENTS))
        raise ValueError(f"Unsupported agent '{agent}'. Supported: {supported}")

    _, config = _resolve(agent)

    created: list[Path] = []
    for key, content in _CONTENT_MAP.items():
        if key in config:
            path = workspace / config[key]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            created.append(path)

    return created
