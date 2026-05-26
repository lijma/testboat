"""testboat validate — pre-report health check across all artifacts."""

from __future__ import annotations
from testboat.commands.active import active_dir

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from testboat.commands.bug import list_bugs
from testboat.commands.case import list_cases, validate_case
from testboat.commands.plan import list_plans, show_plan
from testboat.commands.result import get_matrix
from testboat.commands.strategy import STRATEGY_FILE, validate_strategy


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    name: str
    passed: bool
    details: list[str] = field(default_factory=list)


@dataclass
class ValidateReport:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def counts(self) -> tuple[int, int]:
        passed = sum(1 for c in self.checks if c.passed)
        return passed, len(self.checks)


# ---------------------------------------------------------------------------
# Check 1: Format validation
# ---------------------------------------------------------------------------

def _check_format(testboat_root: Path) -> CheckResult:
    """Validate strategy.yaml and all TC yamls against their schemas."""
    details: list[str] = []
    passed = True

    # strategy.yaml
    strategy_path = active_dir(testboat_root) / STRATEGY_FILE
    if not strategy_path.exists():
        details.append("✗ strategy.yaml not found — run `testboat strategy create`")
        passed = False
    else:
        errors = validate_strategy(testboat_root)
        if errors:
            passed = False
            for e in errors:
                details.append(f"  ✗ strategy.yaml: {e}")
        else:
            details.append("✓ strategy.yaml valid")

    # test cases
    cases = list_cases(testboat_root)
    if not cases:
        details.append("✗ no test cases found")
        passed = False
    else:
        tc_errors: list[str] = []
        for c in cases:
            errs = validate_case(testboat_root, c["id"])
            for e in errs:
                tc_errors.append(f"  ✗ {c['id']}: {e}")
        if tc_errors:
            passed = False
            details.append(f"✗ {len(tc_errors)} test case validation error(s):")
            details.extend(tc_errors)
        else:
            details.append(f"✓ {len(cases)}/{len(cases)} test cases valid")

    return CheckResult("1. Format Validation", passed, details)


# ---------------------------------------------------------------------------
# Check 2: Requirements coverage
# ---------------------------------------------------------------------------

def _check_requirements_coverage(testboat_root: Path) -> CheckResult:
    """Check that all TCs have req_id set (traceability)."""
    details: list[str] = []
    passed = True

    cases = list_cases(testboat_root)
    if not cases:
        return CheckResult("2. Requirements Coverage", False,
                           ["✗ no test cases — nothing to check"])

    covered: list[str] = []
    uncovered: list[str] = []
    req_map: dict[str, list[str]] = {}

    for c in cases:
        req_id = c.get("req_id", "").strip()
        if req_id:
            covered.append(c["id"])
            req_map.setdefault(req_id, []).append(c["id"])
        else:
            uncovered.append(c["id"])

    if uncovered:
        passed = False
        details.append(f"✗ {len(uncovered)} TC(s) have no req_id (untracked):")
        for tc in uncovered:
            details.append(f"  ✗ {tc}")
    else:
        details.append(f"✓ all {len(cases)} TCs have req_id set")

    if req_map:
        details.append(f"  Requirements covered: {len(req_map)} unique req_id(s)")
        for req, tcs in sorted(req_map.items()):
            details.append(f"  {req} → {', '.join(tcs)}")

    return CheckResult("2. Requirements Coverage", passed, details)


# ---------------------------------------------------------------------------
# Check 3: Execution completeness
# ---------------------------------------------------------------------------

def _check_execution_completeness(testboat_root: Path) -> CheckResult:
    """Check all non-draft TCs have at least one execution result."""
    details: list[str] = []
    passed = True

    cases = list_cases(testboat_root)
    matrix = get_matrix(testboat_root)

    non_draft = [c for c in cases if c.get("status") != "draft"]
    if not non_draft:
        return CheckResult("3. Execution Completeness", False,
                           ["✗ no test cases in ready/pass/fail status"])

    not_executed: list[str] = []
    for c in non_draft:
        if c["id"] not in matrix:
            not_executed.append(c["id"])

    if not_executed:
        passed = False
        details.append(f"✗ {len(not_executed)} TC(s) have no execution record:")
        for tc in not_executed:
            details.append(f"  ✗ {tc}")
    else:
        details.append(f"✓ {len(non_draft)}/{len(non_draft)} non-draft TCs executed")

    # Show pass/fail summary
    results_by_status: dict[str, int] = {}
    for tc_id, entry in matrix.items():
        s = entry.get("latest_status", "unknown")
        results_by_status[s] = results_by_status.get(s, 0) + 1
    for s, count in sorted(results_by_status.items()):
        icon = "✓" if s == "pass" else "✗"
        details.append(f"  {icon} {s}: {count}")

    return CheckResult("3. Execution Completeness", passed, details)


# ---------------------------------------------------------------------------
# Check 4: Exit criteria compliance
# ---------------------------------------------------------------------------

def _check_exit_criteria(testboat_root: Path) -> CheckResult:
    """Check bugs and results meet strategy exit criteria."""
    details: list[str] = []
    passed = True

    strategy_path = active_dir(testboat_root) / STRATEGY_FILE
    if not strategy_path.exists():
        return CheckResult("4. Exit Criteria", False,
                           ["✗ strategy.yaml not found — cannot check exit criteria"])

    strategy = yaml.safe_load(strategy_path.read_text(encoding="utf-8"))
    metrics = strategy.get("metrics", {})
    severity_rules: list[dict] = metrics.get("severity", [])

    bugs = list_bugs(testboat_root)
    open_bugs = [b for b in bugs if b["status"] not in ("closed", "wont-fix", "deferred")]

    if not severity_rules:
        details.append("⚠ no severity rules defined in strategy.yaml metrics")
    else:
        for rule in severity_rules:
            level = rule.get("level", "")
            acceptable = rule.get("acceptable", 0)
            count = sum(1 for b in open_bugs if b.get("priority") == level)
            if count > acceptable:
                passed = False
                details.append(f"✗ {level}: {count} open bug(s) (acceptable: {acceptable})")
            else:
                details.append(f"✓ {level}: {count} open bug(s) (acceptable: {acceptable})")

    # TC pass rate
    matrix = get_matrix(testboat_root)
    if matrix:
        total = len(matrix)
        passing = sum(1 for e in matrix.values() if e.get("latest_status") == "pass")
        rate = passing / total * 100
        icon = "✓" if passing == total else "✗"
        details.append(f"{icon} TC pass rate: {passing}/{total} ({rate:.0f}%)")
        if passing < total:
            passed = False

    exit_criteria = strategy.get("exit_criteria", [])
    if exit_criteria:
        details.append("  Exit criteria from strategy:")
        for criterion in exit_criteria:
            details.append(f"  · {criterion}")

    return CheckResult("4. Exit Criteria", passed, details)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_validate(testboat_root: Path) -> ValidateReport:
    """Run all 4 validation checks and return a ValidateReport."""
    report = ValidateReport()
    report.checks.append(_check_format(testboat_root))
    report.checks.append(_check_requirements_coverage(testboat_root))
    report.checks.append(_check_execution_completeness(testboat_root))
    report.checks.append(_check_exit_criteria(testboat_root))
    return report
