"""ftest CLI entry point."""

import threading
from pathlib import Path
from typing import Annotated, Optional

import yaml
import typer

from ftest.commands.case import (
    CaseStatus,
    add_case,
    list_cases,
    set_status,
    show_case,
    validate_case,
    validate_cases_batch,
)
from ftest.commands.bug import (
    BugPriority,
    BugStatus,
    Severity,
    add_bug,
    list_bugs,
    set_bug_status,
    show_bug,
)
from ftest.commands.enable import AGENTS, _CONTENT_MAP, _resolve, enable_agent
from ftest.commands.init import DRAFT_SUBDIRS, init_workspace
from ftest.commands.plan import (
    ExecutionType,
    PlanStatus,
    create_plan,
    list_plans,
    register_automation,
    set_plan_status,
    show_plan,
)
from ftest.commands.result import (
    ResultStatus,
    get_matrix,
    list_results,
    record_result,
    show_result,
)
from ftest.commands.preview import export_pdf, serve_reports
from ftest.commands.active import get_active_version
from ftest.commands.version import create_version, get_current_active, list_versions, show_version, switch_version
from ftest.commands.report import generate_closure, generate_sprint, generate_strategy
from ftest.commands.strategy import create_strategy, validate_strategy
from ftest.commands.tag import TAG_KINDS, add_tag, list_tags
from ftest.commands.validate import run_validate

app = typer.Typer(
    name="ftest",
    help="像代码一样管理测试 — manage tests like code.",
    no_args_is_help=True,
)

strategy_app = typer.Typer(help="Manage test strategy documents.")
tag_app = typer.Typer(help="Manage sprint / type / module tag registry.")
case_app = typer.Typer(help="Test case CRUD and lifecycle.")
plan_app = typer.Typer(help="Execution plan per test case.")
result_app = typer.Typer(help="Record and query execution results.")
matrix_app = typer.Typer(help="Global execution tracking matrix.")
bug_app = typer.Typer(help="Bug / defect lifecycle management.")

report_app = typer.Typer(help="Generate HTML test reports.")
version_app = typer.Typer(help="Manage named test artifact versions.")

app.add_typer(strategy_app, name="strategy")
app.add_typer(tag_app, name="tag")
app.add_typer(case_app, name="case")
app.add_typer(plan_app, name="plan")
app.add_typer(result_app, name="result")
app.add_typer(matrix_app, name="matrix")
app.add_typer(bug_app, name="bug")
app.add_typer(report_app, name="report")
app.add_typer(version_app, name="version")


def _workspace(workspace: Optional[Path]) -> Path:
    target = (workspace or Path.cwd()).resolve()
    if not target.is_dir():
        typer.echo(f"Error: {target} is not a directory.", err=True)
        raise typer.Exit(code=1)
    return target


# ---------------------------------------------------------------------------
# ftest init
# ---------------------------------------------------------------------------


@app.callback()
def _main() -> None:
    """ftest — manage tests like code."""


@app.command()
def init(
    workspace: Annotated[
        Optional[Path],
        typer.Argument(help="Workspace directory (defaults to current directory)."),
    ] = None,
) -> None:
    """Initialise (or refresh) .ftest/ runtime directory in the workspace."""
    target = _workspace(workspace)
    ftest_path = init_workspace(target)
    typer.echo(f"Initialized ftest workspace at {ftest_path}")
    typer.echo("  draft/  ← current working version")
    for subdir in DRAFT_SUBDIRS:
        typer.echo(f"    {subdir}/")
    typer.echo("    ftest.yaml")


# ---------------------------------------------------------------------------
# ftest enable
# ---------------------------------------------------------------------------


@app.command()
def enable(
    agent: Annotated[str, typer.Argument(help=f"Agent name: {', '.join(sorted(AGENTS))} (or 'list')")],
    workspace: Annotated[
        Optional[Path],
        typer.Option("--workspace", "-w", help="Workspace directory (defaults to current directory)."),
    ] = None,
) -> None:
    """Create (or overwrite) ftest rules + skill files for the specified agent."""
    if agent == "list":
        typer.echo("Supported agents:")
        for name in sorted(AGENTS):
            config = AGENTS[name]
            if "alias" in config:
                typer.echo(f"  {name:<12} → alias for {config['alias']}")
                continue
            for f in [config[k] for k in _CONTENT_MAP if k in config]:
                typer.echo(f"  {name:<12} → {f}")
        return

    target = _workspace(workspace)
    try:
        created = enable_agent(target, agent)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    canonical, _ = _resolve(agent.lower())
    label = agent if agent.lower() == canonical else f"{agent} (→ {canonical})"
    typer.echo(f"Enabled ftest for '{label}':")
    for path in created:
        typer.echo(f"  → {path.relative_to(target)}")


# ---------------------------------------------------------------------------
# ftest strategy
# ---------------------------------------------------------------------------


@strategy_app.callback()
def _strategy_main() -> None:
    """Manage test strategy documents."""


@strategy_app.command("create")
def strategy_create(
    workspace: Annotated[Optional[Path], typer.Argument(help="Workspace directory.")] = None,
) -> None:
    """Create (or reset) strategy.yaml template."""
    target = _workspace(workspace)
    path = create_strategy(target)
    typer.echo(f"Created strategy template at {path.relative_to(target)}")
    typer.echo("  Edit the file, then run: ftest strategy validate")


@strategy_app.command("validate")
def strategy_validate(
    workspace: Annotated[Optional[Path], typer.Argument(help="Workspace directory.")] = None,
) -> None:
    """Validate strategy.yaml against the required schema."""
    target = _workspace(workspace)
    try:
        errors = validate_strategy(target)
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    if errors:
        typer.echo("strategy.yaml validation FAILED:", err=True)
        for err in errors:
            typer.echo(f"  ✗ {err}", err=True)
        raise typer.Exit(code=1)
    typer.echo("strategy.yaml is valid ✓")


# ---------------------------------------------------------------------------
# ftest tag
# ---------------------------------------------------------------------------


@tag_app.callback()
def _tag_main() -> None:
    """Manage sprint / type / module tag registry."""


@tag_app.command("add")
def tag_add(
    kind: Annotated[str, typer.Argument(help=f"Tag kind: {', '.join(TAG_KINDS)}")],
    value: Annotated[str, typer.Argument(help="Tag value to add.")],
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """Add a tag value to the registry."""
    target = _workspace(workspace)
    try:
        added = add_tag(target, kind, value)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
    if added:
        typer.echo(f"Added tag {kind}='{value}'")
    else:
        typer.echo(f"Tag {kind}='{value}' already exists")


@tag_app.command("list")
def tag_list(
    workspace: Annotated[Optional[Path], typer.Argument(help="Workspace directory.")] = None,
) -> None:
    """List all registered tags grouped by kind."""
    target = _workspace(workspace)
    tags = list_tags(target)
    for kind in TAG_KINDS:
        values = tags.get(kind, [])
        typer.echo(f"{kind}:")
        if values:
            for v in values:
                typer.echo(f"  - {v}")
        else:
            typer.echo("  (empty)")


# ---------------------------------------------------------------------------
# ftest case
# ---------------------------------------------------------------------------


@case_app.callback()
def _case_main() -> None:
    """Test case CRUD and lifecycle."""


@case_app.command("add")
def case_add(
    title: Annotated[str, typer.Option("--title", "-t", help="Test case title.")],
    priority: Annotated[str, typer.Option("--priority", "-p", help="P0/P1/P2/P3.")] = "P2",
    sprint: Annotated[Optional[str], typer.Option("--sprint", help="Sprint tag.")] = None,
    type_: Annotated[Optional[str], typer.Option("--type", help="Type tag.")] = None,
    module: Annotated[Optional[str], typer.Option("--module", help="Module tag.")] = None,
    req_id: Annotated[str, typer.Option("--req-id", help="Linked requirement ID.")] = "",
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """Create a new test case (metadata skeleton — AI fills in steps)."""
    target = _workspace(workspace)
    try:
        path = add_case(target, title, priority=priority,
                        sprint=sprint, type_=type_, module=module, req_id=req_id)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
    tc_id = path.stem
    typer.echo(f"Created {tc_id}: {title}")
    typer.echo(f"  → {path.relative_to(target)}")
    typer.echo("  Next: ask AI to fill in steps, then run: ftest case validate " + tc_id)


@case_app.command("list")
def case_list(
    sprint: Annotated[Optional[str], typer.Option("--sprint")] = None,
    type_: Annotated[Optional[str], typer.Option("--type")] = None,
    module: Annotated[Optional[str], typer.Option("--module")] = None,
    status: Annotated[Optional[str], typer.Option("--status")] = None,
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """List test cases with optional filters."""
    target = _workspace(workspace)
    cases = list_cases(target, sprint=sprint, type_=type_, module=module, status=status)
    if not cases:
        typer.echo("No test cases found.")
        return
    typer.echo(f"{'ID':<10} {'STATUS':<10} {'PRI':<5} {'TITLE'}")
    typer.echo("─" * 60)
    for c in cases:
        typer.echo(f"{c['id']:<10} {c['status']:<10} {c['priority']:<5} {c['title']}")


@case_app.command("show")
def case_show(
    tc_id: Annotated[str, typer.Argument(help="Test case ID, e.g. TC-001.")],
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """Show full details of a test case."""
    target = _workspace(workspace)
    try:
        data = show_case(target, tc_id)
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo(yaml.dump(data, default_flow_style=False, allow_unicode=True))


@case_app.command("status")
def case_status(
    tc_id: Annotated[str, typer.Argument(help="Test case ID.")],
    new_status: Annotated[str, typer.Argument(help=f"New status: {', '.join(s.value for s in CaseStatus)}")],
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """Transition a test case to a new status."""
    target = _workspace(workspace)
    try:
        set_status(target, tc_id, new_status)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"{tc_id} → {new_status}")


@case_app.command("validate")
def case_validate(
    tc_id: Annotated[str, typer.Argument(
        help="Test case ID (e.g. TC-001), or 'all' to validate every case."
    )],
    sprint: Annotated[Optional[str], typer.Option("--sprint")] = None,
    type_: Annotated[Optional[str], typer.Option("--type")] = None,
    module: Annotated[Optional[str], typer.Option("--module")] = None,
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """Validate one case, or batch-validate by 'all' / tag filters."""
    target = _workspace(workspace)

    # Batch mode: 'all' keyword or any tag filter provided
    if tc_id == "all" or sprint or type_ or module:
        results = validate_cases_batch(
            target,
            sprint=sprint,
            type_=type_,
            module=module,
        )
        failed = {k: v for k, v in results.items() if v}

        if not results:
            typer.echo("No test cases found.")
            return

        for tc, errors in sorted(results.items()):
            if errors:
                typer.echo(f"{tc} FAILED:")
                for err in errors:
                    typer.echo(f"  ✗ {err}")
            else:
                typer.echo(f"{tc} ✓")

        total = len(results)
        typer.echo(f"\n{total - len(failed)}/{total} valid")
        if failed:
            raise typer.Exit(code=1)
        return

    # Single case mode
    try:
        errors = validate_case(target, tc_id)
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
    if errors:
        typer.echo(f"{tc_id} validation FAILED:", err=True)
        for err in errors:
            typer.echo(f"  ✗ {err}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"{tc_id} is valid ✓")


# ---------------------------------------------------------------------------
# ftest plan
# ---------------------------------------------------------------------------


@plan_app.callback()
def _plan_main() -> None:
    """Execution plan per test case."""


@plan_app.command("create")
def plan_create(
    tc_id: Annotated[str, typer.Argument(help="Test case ID.")],
    execution_type: Annotated[str, typer.Option("--type", help="manual/automated/both.")] = "manual",
    tool: Annotated[Optional[str], typer.Option("--tool", help="Automation tool.")] = None,
    executor: Annotated[Optional[str], typer.Option("--executor", help="Manual executor name.")] = None,
    notes: Annotated[str, typer.Option("--notes")] = "",
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """Create (or overwrite) execution plan for a test case."""
    target = _workspace(workspace)
    try:
        path = create_plan(target, tc_id, execution_type=execution_type,
                           tool=tool, executor=executor, notes=notes)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Created plan for {tc_id} → {path.relative_to(target)}")


@plan_app.command("list")
def plan_list(
    execution_type: Annotated[Optional[str], typer.Option("--type")] = None,
    status: Annotated[Optional[str], typer.Option("--status")] = None,
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """List execution plans."""
    target = _workspace(workspace)
    plans = list_plans(target, execution_type=execution_type, status=status)
    if not plans:
        typer.echo("No plans found.")
        return
    typer.echo(f"{'TC':<10} {'TYPE':<12} {'TOOL':<12} {'STATUS'}")
    typer.echo("─" * 50)
    for p in plans:
        typer.echo(f"{p['tc_id']:<10} {p['execution_type']:<12} "
                   f"{(p['automation_tool'] or '-'):<12} {p['status']}")


@plan_app.command("show")
def plan_show(
    tc_id: Annotated[str, typer.Argument(help="Test case ID.")],
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """Show full plan details."""
    target = _workspace(workspace)
    try:
        data = show_plan(target, tc_id)
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo(yaml.dump(data, default_flow_style=False, allow_unicode=True))


@plan_app.command("status")
def plan_status(
    tc_id: Annotated[str, typer.Argument(help="Test case ID.")],
    new_status: Annotated[str, typer.Argument(help=f"New status: {', '.join(s.value for s in PlanStatus)}")],
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """Update plan status (draft → approved)."""
    target = _workspace(workspace)
    try:
        set_plan_status(target, tc_id, new_status)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"{tc_id} plan → {new_status}")


@plan_app.command("register")
def plan_register(
    tc_id: Annotated[str, typer.Argument(help="Test case ID.")],
    script_path: Annotated[str, typer.Argument(help="Script path relative to workspace root.")],
    tool: Annotated[Optional[str], typer.Option("--tool", help="Override tool (auto-detected from extension).")] = None,
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """Register an automation script to a test case plan."""
    target = _workspace(workspace)
    try:
        path = register_automation(target, tc_id, script_path, tool=tool)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
    data = show_plan(target, tc_id)
    typer.echo(f"Registered {tc_id}: {data['automation_tool']} → {script_path}")


# ---------------------------------------------------------------------------
# ftest result
# ---------------------------------------------------------------------------


@result_app.callback()
def _result_main() -> None:
    """Record and query execution results."""


@result_app.command("record")
def result_record(
    tc_id: Annotated[str, typer.Argument(help="Test case ID.")],
    status: Annotated[str, typer.Argument(help=f"Result: {', '.join(s.value for s in ResultStatus)}")],
    execution_type: Annotated[str, typer.Option("--type", help="manual/automated.")] = "manual",
    by: Annotated[str, typer.Option("--by", help="Executed by.")] = "",
    duration: Annotated[str, typer.Option("--duration")] = "",
    notes: Annotated[str, typer.Option("--notes")] = "",
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """Record one execution result and update the tracking matrix."""
    target = _workspace(workspace)
    try:
        path = record_result(target, tc_id, status, execution_type=execution_type,
                             by=by, duration=duration, notes=notes)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
    res_id = path.stem
    typer.echo(f"Recorded {res_id}: {tc_id} → {status}")


@result_app.command("list")
def result_list(
    tc_id: Annotated[Optional[str], typer.Option("--tc", help="Filter by TC ID.")] = None,
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """List execution results."""
    target = _workspace(workspace)
    results = list_results(target, tc_id=tc_id)
    if not results:
        typer.echo("No results found.")
        return
    typer.echo(f"{'ID':<10} {'TC':<10} {'TYPE':<12} {'STATUS':<10} {'EXECUTED AT'}")
    typer.echo("─" * 65)
    for r in results:
        typer.echo(f"{r['id']:<10} {r['tc_id']:<10} {r['execution_type']:<12} "
                   f"{r['status']:<10} {r['executed_at']}")


@result_app.command("show")
def result_show(
    res_id: Annotated[str, typer.Argument(help="Result ID, e.g. RES-001.")],
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """Show full result details."""
    target = _workspace(workspace)
    try:
        data = show_result(target, res_id)
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo(yaml.dump(data, default_flow_style=False, allow_unicode=True))


# ---------------------------------------------------------------------------
# ftest matrix
# ---------------------------------------------------------------------------


@matrix_app.callback()
def _matrix_main() -> None:
    """Global execution tracking matrix."""


@matrix_app.command("show")
def matrix_show(
    tc_id: Annotated[Optional[str], typer.Argument(help="TC ID to filter, or omit for all.")] = None,
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """Show execution matrix (latest status per TC)."""
    target = _workspace(workspace)
    matrix = get_matrix(target, tc_id=tc_id)
    if not matrix:
        typer.echo("No execution data yet.")
        return
    typer.echo(f"{'TC':<10} {'LATEST':<10} {'RUNS':<6} {'TYPES'}")
    typer.echo("─" * 55)
    for tc, entry in sorted(matrix.items()):
        types = ", ".join(entry.get("execution_types_used", []))
        runs = len(entry.get("result_ids", []))
        typer.echo(f"{tc:<10} {entry['latest_status']:<10} {runs:<6} {types}")


# ---------------------------------------------------------------------------
# ftest exec
# ---------------------------------------------------------------------------
# ftest bug
# ---------------------------------------------------------------------------


@bug_app.callback()
def _bug_main() -> None:
    """Bug / defect lifecycle management."""


@bug_app.command("add")
def bug_add(
    title: Annotated[str, typer.Option("--title", "-t", help="Bug title.")],
    severity: Annotated[str, typer.Option("--severity", help="critical/major/minor/cosmetic.")] = "major",
    priority: Annotated[str, typer.Option("--priority", "-p", help="P0/P1/P2/P3.")] = "P2",
    sprint: Annotated[Optional[str], typer.Option("--sprint", help="Sprint tag.")] = None,
    type_: Annotated[Optional[str], typer.Option("--type", help="Type tag.")] = None,
    module: Annotated[Optional[str], typer.Option("--module", help="Module tag.")] = None,
    tc_id: Annotated[str, typer.Option("--tc", help="Linked test case ID.")] = "",
    result_id: Annotated[str, typer.Option("--result", help="Linked result ID.")] = "",
    environment: Annotated[str, typer.Option("--env", help="Environment where found.")] = "",
    notes: Annotated[str, typer.Option("--notes")] = "",
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """Create a new bug report."""
    target = _workspace(workspace)
    try:
        path = add_bug(target, title, severity=severity, priority=priority,
                       tc_id=tc_id, result_id=result_id, environment=environment,
                       notes=notes, sprint=sprint, type_=type_, module=module)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
    bug_id = path.stem
    typer.echo(f"Created {bug_id}: [{severity.upper()}][{priority}] {title}")


@bug_app.command("list")
def bug_list(
    status: Annotated[Optional[str], typer.Option("--status")] = None,
    severity: Annotated[Optional[str], typer.Option("--severity")] = None,
    priority: Annotated[Optional[str], typer.Option("--priority")] = None,
    sprint: Annotated[Optional[str], typer.Option("--sprint")] = None,
    type_: Annotated[Optional[str], typer.Option("--type")] = None,
    module: Annotated[Optional[str], typer.Option("--module")] = None,
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """List bugs with optional filters."""
    target = _workspace(workspace)
    bugs = list_bugs(target, status=status, severity=severity, priority=priority,
                     sprint=sprint, type_=type_, module=module)
    if not bugs:
        typer.echo("No bugs found.")
        return
    typer.echo(f"{'ID':<10} {'SEV':<10} {'PRI':<5} {'STATUS':<16} {'TITLE'}")
    typer.echo("─" * 70)
    for b in bugs:
        typer.echo(f"{b['id']:<10} {b['severity']:<10} {b['priority']:<5} "
                   f"{b['status']:<16} {b['title']}")


@bug_app.command("show")
def bug_show(
    bug_id: Annotated[str, typer.Argument(help="Bug ID, e.g. BUG-001.")],
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """Show full bug details."""
    target = _workspace(workspace)
    try:
        data = show_bug(target, bug_id)
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo(yaml.dump(data, default_flow_style=False, allow_unicode=True))


@bug_app.command("status")
def bug_status(
    bug_id: Annotated[str, typer.Argument(help="Bug ID.")],
    new_status: Annotated[str, typer.Argument(
        help=f"New status: {', '.join(s.value for s in BugStatus)}"
    )],
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """Transition a bug to a new status."""
    target = _workspace(workspace)
    try:
        set_bug_status(target, bug_id, new_status)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"{bug_id} → {new_status}")


# ---------------------------------------------------------------------------
# ftest report
# ---------------------------------------------------------------------------


@report_app.callback()
def _report_main() -> None:
    """Generate HTML test reports."""


@report_app.command("strategy")
def report_strategy(
    workspace: Annotated[Optional[Path], typer.Argument(help="Workspace directory.")] = None,
) -> None:
    """Generate strategy HTML report from strategy.yaml."""
    target = _workspace(workspace)
    path = generate_strategy(target)
    typer.echo(f"Generated → {path.relative_to(target)}")


@report_app.command("sprint")
def report_sprint(
    workspace: Annotated[Optional[Path], typer.Argument(help="Workspace directory.")] = None,
) -> None:
    """Generate sprint test report (cases + execution + bugs)."""
    target = _workspace(workspace)
    path = generate_sprint(target)
    typer.echo(f"Generated → {path.relative_to(target)}")
    typer.echo("  Run `ftest preview` to open in browser.")


@report_app.command("closure")
def report_closure(
    summary: Annotated[str, typer.Option("--summary", help="Executive summary (AI-generated narrative).")] = "",
    workspace: Annotated[Optional[Path], typer.Argument(help="Workspace directory.")] = None,
) -> None:
    """Generate test closure report with metrics and sign-off status."""
    target = _workspace(workspace)
    path = generate_closure(target, summary=summary)
    typer.echo(f"Generated → {path.relative_to(target)}")
    typer.echo("  Run `ftest preview` to open in browser.")


# ---------------------------------------------------------------------------
# ftest preview
# ---------------------------------------------------------------------------


@app.command("preview")
def preview_cmd(
    pdf: Annotated[Optional[str], typer.Option("--pdf", help="Export specific HTML file to PDF.")] = None,
    port: Annotated[Optional[int], typer.Option("--port", help="Port (random if omitted).")] = None,
    no_browser: Annotated[bool, typer.Option("--no-browser")] = False,
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """Serve reports locally or export a report to PDF."""
    target = _workspace(workspace)

    if pdf:
        html_path = Path(pdf) if Path(pdf).is_absolute() else target / pdf
        if not html_path.exists():
            typer.echo(f"Error: {html_path} not found.", err=True)
            raise typer.Exit(code=1)
        try:
            out = export_pdf(html_path)
            typer.echo(f"PDF exported → {out}")
        except RuntimeError as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(code=1)
        return

    stop = threading.Event()
    chosen_port, url = serve_reports(target, port=port, open_browser=not no_browser,
                                     _stop_event=stop)
    typer.echo(f"Serving reports at {url}")
    typer.echo("  Press Ctrl+C to stop.")
    try:
        stop.wait()
    except KeyboardInterrupt:
        stop.set()
        typer.echo("\nStopped.")


# ---------------------------------------------------------------------------
# ftest validate
# ---------------------------------------------------------------------------


@app.command("validate")
def validate_cmd(
    workspace: Annotated[
        Optional[Path],
        typer.Argument(help="Workspace directory (defaults to current directory)."),
    ] = None,
) -> None:
    """Pre-report health check: format / coverage / execution / exit criteria."""
    target = _workspace(workspace)
    report = run_validate(target)

    passed_n, total_n = report.counts
    for check in report.checks:
        icon = "✓" if check.passed else "✗"
        typer.echo(f"\n{icon} {check.name}")
        for line in check.details:
            typer.echo(f"  {line}")

    typer.echo(f"\n{'─' * 50}")
    typer.echo(f"Result: {passed_n}/{total_n} checks passed")

    if not report.passed:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# ftest version
# ---------------------------------------------------------------------------


@version_app.callback()
def _version_main() -> None:
    """Manage named test artifact versions."""


@version_app.command("create")
def version_create(
    version: Annotated[str, typer.Argument(help="New version name, e.g. v1.0.")],
    base: Annotated[Optional[str], typer.Argument(help="Base version to copy from (omit to use draft).")] = None,
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """Create a named version from draft or from an existing version."""
    target = _workspace(workspace)
    try:
        vdir = create_version(target, version, base=base)
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    if base:
        typer.echo(f"Created version '{version}' based on '{base}' → {vdir.relative_to(target)}")
    else:
        typer.echo(f"Created version '{version}' from draft → {vdir.relative_to(target)}")


@version_app.command("list")
def version_list(
    workspace: Annotated[Optional[Path], typer.Argument(help="Workspace directory.")] = None,
) -> None:
    """List all named versions."""
    target = _workspace(workspace)
    active = get_active_version(target)
    versions = list_versions(target)
    typer.echo(f"Active: {active}\n")
    if not versions:
        typer.echo("No named versions yet. Run `ftest version create <name>` to create one.")
        return
    typer.echo(f"{'VERSION':<12} {'BASE':<12} {'CASES':<7} {'BUGS':<6} {'CREATED AT'}")
    typer.echo("─" * 60)
    for v in versions:
        marker = " ◀ active" if v["version"] == active else ""
        typer.echo(
            f"{v['version']:<12} {(v['base'] or 'draft'):<12} "
            f"{v['cases']:<7} {v['bugs']:<6} {v['created_at']}{marker}"
        )


@version_app.command("switch")
def version_switch(
    version: Annotated[str, typer.Argument(help="Version to activate, e.g. v1.0 or 'draft'.")],
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """Switch the active version (updates .ftest/.active)."""
    target = _workspace(workspace)
    try:
        name = switch_version(target, version)
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Active version → {name}")
    typer.echo("  All ftest commands now operate on this version's directory.")


@version_app.command("active")
def version_active(
    workspace: Annotated[Optional[Path], typer.Argument(help="Workspace directory.")] = None,
) -> None:
    """Show the currently active version."""
    target = _workspace(workspace)
    active = get_current_active(target)
    typer.echo(f"Active: {active}")


@version_app.command("show")
def version_show(
    version: Annotated[str, typer.Argument(help="Version name.")],
    workspace: Annotated[Optional[Path], typer.Option("--workspace", "-w")] = None,
) -> None:
    """Show details of a named version."""
    target = _workspace(workspace)
    try:
        info = show_version(target, version)
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Version  : {info['version']}")
    typer.echo(f"Base     : {info['base'] or 'draft'}")
    typer.echo(f"Created  : {info['created_at']}")
    typer.echo(f"Cases    : {info['cases']}")
    typer.echo(f"Bugs     : {info['bugs']}")
    typer.echo(f"Results  : {info['results']}")


if __name__ == "__main__":
    app()
