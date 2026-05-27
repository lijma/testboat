"""testboat report — generate HTML test reports from .testboat/draft/ artifacts."""

from __future__ import annotations
from testboat.commands.active import active_dir

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, BaseLoader

REPORTS_DIR = "reports"

# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def _load_strategy(testboat_root: Path) -> dict[str, Any]:
    path = active_dir(testboat_root) / "strategy.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_cases(testboat_root: Path) -> list[dict[str, Any]]:
    cases_dir = active_dir(testboat_root) / "cases"
    if not cases_dir.exists():
        return []
    return [
        yaml.safe_load(p.read_text(encoding="utf-8"))
        for p in sorted(cases_dir.glob("TC-*.yaml"))
    ]


def _load_results(testboat_root: Path) -> list[dict[str, Any]]:
    results_dir = active_dir(testboat_root) / "executions" / "results"
    if not results_dir.exists():
        return []
    return [
        yaml.safe_load(p.read_text(encoding="utf-8"))
        for p in sorted(results_dir.glob("RES-*.yaml"))
    ]


def _load_matrix(testboat_root: Path) -> dict[str, Any]:
    path = active_dir(testboat_root) / "executions" / "execution-matrix.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_bugs(testboat_root: Path) -> list[dict[str, Any]]:
    bugs_dir = active_dir(testboat_root) / "bugs"
    if not bugs_dir.exists():
        return []
    return [
        yaml.safe_load(p.read_text(encoding="utf-8"))
        for p in sorted(bugs_dir.glob("BUG-*.yaml"))
    ]


def _reports_dir(testboat_root: Path) -> Path:
    return active_dir(testboat_root) / REPORTS_DIR


# ---------------------------------------------------------------------------
# Shared CSS
# ---------------------------------------------------------------------------

_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       margin: 0; padding: 0; background: #f5f5f5; color: #333; }
.container { max-width: 1100px; margin: 0 auto; padding: 24px; }
h1 { color: #1a1a2e; border-bottom: 3px solid #0066cc; padding-bottom: 8px; }
h2 { color: #0066cc; margin-top: 32px; }
h3 { color: #444; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 12px;
         font-size: 12px; font-weight: 600; }
.badge-pass { background: #d4edda; color: #155724; }
.badge-fail { background: #f8d7da; color: #721c24; }
.badge-new  { background: #fff3cd; color: #856404; }
.badge-closed { background: #e2e3e5; color: #383d41; }
.badge-critical { background: #f8d7da; color: #721c24; }
.badge-major    { background: #fff3cd; color: #856404; }
.badge-minor    { background: #d1ecf1; color: #0c5460; }
.badge-P0 { background: #f8d7da; color: #721c24; }
.badge-P1 { background: #fde8d8; color: #8a4910; }
.badge-P2 { background: #fff3cd; color: #856404; }
.badge-P3 { background: #e2e3e5; color: #383d41; }
table { width: 100%; border-collapse: collapse; background: white;
        box-shadow: 0 1px 3px rgba(0,0,0,.1); border-radius: 8px; overflow: hidden; }
th { background: #0066cc; color: white; padding: 10px 14px; text-align: left; font-size: 13px; }
td { padding: 9px 14px; border-bottom: 1px solid #eee; font-size: 13px; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: #f8f9fa; }
.summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                gap: 16px; margin: 24px 0; }
.summary-card { background: white; border-radius: 8px; padding: 20px;
                box-shadow: 0 1px 3px rgba(0,0,0,.1); text-align: center; }
.summary-card .number { font-size: 36px; font-weight: 700; color: #0066cc; }
.summary-card .label  { font-size: 13px; color: #666; margin-top: 4px; }
.pass-num { color: #28a745 !important; }
.fail-num { color: #dc3545 !important; }
.risk-high   { color: #dc3545; font-weight: 600; }
.risk-medium { color: #fd7e14; font-weight: 600; }
.risk-low    { color: #28a745; }
.meta { color: #666; font-size: 13px; margin-bottom: 24px; }
.section { background: white; border-radius: 8px; padding: 20px;
           box-shadow: 0 1px 3px rgba(0,0,0,.1); margin-bottom: 24px; }
.criteria-pass { color: #28a745; } .criteria-fail { color: #dc3545; }
.tag { display: inline-block; background: #e8f0fe; color: #1a73e8;
       border-radius: 4px; padding: 1px 6px; font-size: 11px; margin: 1px; }
footer { text-align: center; color: #999; font-size: 12px; margin-top: 40px; padding: 16px; }
.tc-row { cursor: pointer; user-select: none; }
.tc-row:hover td { background: #eef4ff !important; }
.tc-chevron { font-size: 9px; color: #888; margin-right: 6px; display: inline-block;
              transition: transform .15s; }
.tc-detail { display: none; }
.tc-detail td { background: #f8fbff; padding: 16px 20px; }
.detail-inner { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.detail-section h4 { font-size: 11px; text-transform: uppercase; letter-spacing: .8px;
                     color: #666; margin-bottom: 8px; border-bottom: 1px solid #dce6f8;
                     padding-bottom: 4px; }
.detail-section ul { padding-left: 16px; font-size: 12px; color: #555; margin: 0; }
.detail-section ul li { margin-bottom: 4px; }
.detail-section p { font-size: 12px; color: #555; margin: 0; line-height: 1.5; }
.steps-tbl { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 12px;
             box-shadow: none; border-radius: 6px; overflow: hidden; background: white; }
.steps-tbl th { background: #e8f0fe; color: #1a73e8; padding: 6px 10px;
                text-align: left; font-size: 11px; }
.steps-tbl td { padding: 6px 10px; border-bottom: 1px solid #e8f0fe;
                vertical-align: top; color: #444; }
.steps-tbl tr:last-child td { border-bottom: none; }
.exec-meta { font-size: 11px; color: #888; margin-top: 10px; }
"""

_TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H:%M")

# ---------------------------------------------------------------------------
# Strategy Report
# ---------------------------------------------------------------------------

_STRATEGY_TMPL = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<title>Test Strategy — {{ strategy.release or 'draft' }}</title>
<style>{{ css }}</style></head>
<body><div class="container">
<h1>📋 Test Strategy Report</h1>
<p class="meta">Release: <strong>{{ strategy.release or '-' }}</strong> &nbsp;|&nbsp;
Status: <strong>{{ strategy.status or 'draft' }}</strong> &nbsp;|&nbsp;
Generated: {{ ts }}</p>

<div class="section">
<h2>Scope</h2>
<h3>In Scope</h3>
<ul>{% for item in strategy.scope.in_scope %}<li>{{ item }}</li>{% endfor %}</ul>
<h3>Out of Scope</h3>
<ul>{% for item in strategy.scope.out_scope %}<li>{{ item }}</li>{% endfor %}</ul>
</div>

<div class="section">
<h2>Risk Matrix</h2>
<table><tr><th>Area</th><th>Likelihood</th><th>Impact</th><th>Approach</th></tr>
{% for r in strategy.risk_matrix %}
<tr>
  <td>{{ r.area }}</td>
  <td class="risk-{{ r.likelihood }}">{{ r.likelihood }}</td>
  <td class="risk-{{ r.impact }}">{{ r.impact }}</td>
  <td>{{ r.approach }}</td>
</tr>{% endfor %}
</table></div>

<div class="section">
<h2>Entry / Exit Criteria</h2>
<h3>Entry Criteria</h3>
<ul>{% for c in strategy.entry_criteria %}<li>{{ c }}</li>{% endfor %}</ul>
<h3>Exit Criteria</h3>
<ul>{% for c in strategy.exit_criteria %}<li>{{ c }}</li>{% endfor %}</ul>
</div>

<div class="section">
<h2>Metrics &amp; Severity</h2>
<table><tr><th>Level</th><th>Description</th><th>Acceptable Open</th></tr>
{% for s in strategy.metrics.severity %}
<tr><td><span class="badge badge-{{ s.level }}">{{ s.level }}</span></td>
    <td>{{ s.description }}</td><td>{{ s.acceptable }}</td></tr>
{% endfor %}</table></div>

<footer>Generated by testboat · {{ ts }}</footer>
</div></body></html>"""

# ---------------------------------------------------------------------------
# Sprint Report
# ---------------------------------------------------------------------------

_SPRINT_TMPL = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<title>Sprint Test Report — {{ release }}</title>
<style>{{ css }}</style></head>
<body><div class="container">
<h1>🧪 Sprint Test Report</h1>
<p class="meta">Release: <strong>{{ release }}</strong> &nbsp;|&nbsp; Generated: {{ ts }}</p>

<div class="summary-grid">
  <div class="summary-card"><div class="number">{{ total_cases }}</div><div class="label">Test Cases</div></div>
  <div class="summary-card"><div class="number pass-num">{{ pass_count }}</div><div class="label">Passed</div></div>
  <div class="summary-card"><div class="number fail-num">{{ fail_count }}</div><div class="label">Failed</div></div>
  <div class="summary-card"><div class="number">{{ not_run }}</div><div class="label">Not Run</div></div>
  <div class="summary-card"><div class="number fail-num">{{ open_bugs }}</div><div class="label">Open Bugs</div></div>
  <div class="summary-card"><div class="number">{{ pass_rate }}%</div><div class="label">Pass Rate</div></div>
</div>

<div class="section">
<h2>Test Cases</h2>
<table><tr><th>ID</th><th>Title</th><th>Module</th><th>Type</th><th>Status</th><th>Latest Result</th></tr>
{% for c in cases %}
<tr class="tc-row" onclick="toggleTC('{{ c.id }}')">
  <td><span class="tc-chevron" id="chev-{{ c.id }}">▶</span>{{ c.id }}</td>
  <td>{{ c.title }}</td>
  <td><span class="tag">{{ c.tags.module or '-' }}</span></td>
  <td><span class="tag">{{ c.tags.type or '-' }}</span></td>
  <td><span class="badge badge-{{ c.status }}">{{ c.status }}</span></td>
  <td>{% if c.id in matrix %}<span class="badge badge-{{ matrix[c.id].latest_status }}">{{ matrix[c.id].latest_status }}</span>{% else %}-{% endif %}</td>
</tr>
<tr class="tc-detail" id="detail-{{ c.id }}">
  <td colspan="6">
    <div class="detail-inner">
      <div class="detail-section">
        <h4>Preconditions</h4>
        {% if c.preconditions %}<ul>{% for p in c.preconditions %}<li>{{ p }}</li>{% endfor %}</ul>
        {% else %}<p>—</p>{% endif %}
      </div>
      <div class="detail-section">
        <h4>Expected Result</h4>
        <p>{{ c.expected_result or '—' }}</p>
        {% if results_by_tc.get(c.id) %}
        <p class="exec-meta">
          Executed: {{ results_by_tc[c.id].executed_at or '—' }} &nbsp;·&nbsp;
          By: {{ results_by_tc[c.id].executed_by or '—' }} &nbsp;·&nbsp;
          Type: {{ results_by_tc[c.id].execution_type or '—' }}
        </p>{% endif %}
      </div>
    </div>
    {% if c.steps %}
    <table class="steps-tbl">
      <tr><th style="width:30px">#</th><th style="width:50%">Action</th><th>Expected</th></tr>
      {% for s in c.steps %}
      <tr>
        <td>{{ loop.index }}</td>
        <td>{{ s.action }}</td>
        <td>{{ s.expected }}</td>
      </tr>{% endfor %}
    </table>{% endif %}
  </td>
</tr>
{% endfor %}
</table></div>
<script>
function toggleTC(id) {
  var row = document.getElementById('detail-' + id);
  var chev = document.getElementById('chev-' + id);
  if (row.style.display === 'table-row') {
    row.style.display = 'none';
    chev.textContent = '▶';
  } else {
    row.style.display = 'table-row';
    chev.textContent = '▼';
  }
}
</script>

<div class="section">
<h2>Bugs ({{ bugs|length }} total)</h2>
{% if bugs %}
<table><tr><th>ID</th><th>Title</th><th>Severity</th><th>Priority</th><th>Status</th><th>Module</th></tr>
{% for b in bugs %}
<tr>
  <td>{{ b.id }}</td><td>{{ b.title }}</td>
  <td><span class="badge badge-{{ b.severity }}">{{ b.severity }}</span></td>
  <td><span class="badge badge-{{ b.priority }}">{{ b.priority }}</span></td>
  <td><span class="badge badge-{{ b.status }}">{{ b.status }}</span></td>
  <td><span class="tag">{{ (b.tags or {}).get('module') or '-' }}</span></td>
</tr>{% endfor %}
</table>
{% else %}<p>No bugs filed.</p>{% endif %}
</div>

<footer>Generated by testboat · {{ ts }}</footer>
</div></body></html>"""

# ---------------------------------------------------------------------------
# Closure Report
# ---------------------------------------------------------------------------

_CLOSURE_TMPL = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<title>Test Closure Report — {{ release }}</title>
<style>{{ css }}</style></head>
<body><div class="container">
<h1>📊 Test Closure Report</h1>
<p class="meta">Release: <strong>{{ release }}</strong> &nbsp;|&nbsp; Generated: {{ ts }}</p>

<div class="section">
<h2>Executive Summary</h2>
<p>{{ summary }}</p>
</div>

<div class="summary-grid">
  <div class="summary-card"><div class="number">{{ total_cases }}</div><div class="label">Total TCs</div></div>
  <div class="summary-card"><div class="number pass-num">{{ pass_count }}</div><div class="label">Passed</div></div>
  <div class="summary-card"><div class="number fail-num">{{ fail_count }}</div><div class="label">Failed</div></div>
  <div class="summary-card"><div class="number">{{ pass_rate }}%</div><div class="label">Pass Rate</div></div>
  <div class="summary-card"><div class="number fail-num">{{ open_bugs }}</div><div class="label">Open Bugs</div></div>
  <div class="summary-card"><div class="number">{{ closed_bugs }}</div><div class="label">Closed Bugs</div></div>
</div>

<div class="section">
<h2>Metrics vs Exit Criteria</h2>
<table><tr><th>Level</th><th>Open Bugs</th><th>Acceptable</th><th>Status</th></tr>
{% for row in metrics_rows %}
<tr>
  <td><span class="badge badge-{{ row.level }}">{{ row.level }}</span></td>
  <td>{{ row.open }}</td><td>{{ row.acceptable }}</td>
  <td class="{% if row.passed %}criteria-pass{% else %}criteria-fail{% endif %}">
    {% if row.passed %}✓ Pass{% else %}✗ Fail{% endif %}</td>
</tr>{% endfor %}
</table>
<p style="margin-top:12px">TC Pass Rate:
  <strong class="{% if pass_rate == 100 %}criteria-pass{% else %}criteria-fail{% endif %}">
  {{ pass_rate }}%</strong>
</p>
</div>

<div class="section">
<h2>Exit Criteria Checklist</h2>
<ul>{% for c in exit_criteria %}
  <li class="{% if criteria_met %}criteria-pass{% else %}criteria-fail{% endif %}">{{ c }}</li>
{% endfor %}</ul>
<p><strong>Overall Sign-off: </strong>
  <span class="{% if criteria_met %}criteria-pass{% else %}criteria-fail{% endif %}" style="font-size:18px">
  {% if criteria_met %}✓ READY FOR RELEASE{% else %}✗ NOT READY — issues remain{% endif %}
  </span></p>
</div>

<div class="section">
<h2>Bug Summary</h2>
<table><tr><th>ID</th><th>Title</th><th>Severity</th><th>Priority</th><th>Status</th></tr>
{% for b in bugs %}
<tr>
  <td>{{ b.id }}</td><td>{{ b.title }}</td>
  <td><span class="badge badge-{{ b.severity }}">{{ b.severity }}</span></td>
  <td><span class="badge badge-{{ b.priority }}">{{ b.priority }}</span></td>
  <td><span class="badge badge-{{ b.status }}">{{ b.status }}</span></td>
</tr>{% endfor %}
</table>
</div>

<footer>Generated by testboat · {{ ts }}</footer>
</div></body></html>"""


# ---------------------------------------------------------------------------
# Render functions
# ---------------------------------------------------------------------------

def _render(template_str: str, **ctx: Any) -> str:
    env = Environment(loader=BaseLoader())
    tmpl = env.from_string(template_str)
    return tmpl.render(css=_CSS, ts=_TIMESTAMP, **ctx)


def _write_report(testboat_root: Path, filename: str, html: str) -> Path:
    out = _reports_dir(testboat_root)
    out.mkdir(parents=True, exist_ok=True)
    path = out / filename
    path.write_text(html, encoding="utf-8")
    return path


def generate_strategy(testboat_root: Path) -> Path:
    """Render strategy.yaml → strategy.html. Returns output path."""
    strategy = _load_strategy(testboat_root)
    # ensure nested keys exist so template never raises KeyError
    strategy.setdefault("scope", {"in_scope": [], "out_scope": []})
    strategy.setdefault("risk_matrix", [])
    strategy.setdefault("entry_criteria", [])
    strategy.setdefault("exit_criteria", [])
    strategy.setdefault("metrics", {"severity": []})
    release = strategy.get("release", "draft")
    html = _render(_STRATEGY_TMPL, strategy=strategy)
    return _write_report(testboat_root, f"strategy-{release}.html", html)


def _compute_sprint_data(
    testboat_root: Path,
) -> dict[str, Any]:
    strategy = _load_strategy(testboat_root)
    cases = _load_cases(testboat_root)
    matrix = _load_matrix(testboat_root)
    bugs = _load_bugs(testboat_root)
    results = _load_results(testboat_root)

    total = len(cases)
    pass_count = sum(1 for c in cases
                     if matrix.get(c.get("id"), {}).get("latest_status") == "pass")
    fail_count = sum(1 for c in cases
                     if matrix.get(c.get("id"), {}).get("latest_status") == "fail")
    not_run = total - sum(1 for tc_id in matrix)
    open_bugs = sum(1 for b in bugs
                    if b.get("status") not in ("closed", "wont-fix", "deferred"))
    pass_rate = round(pass_count / total * 100) if total else 0

    results_by_id = {r.get("id"): r for r in results}
    results_by_tc: dict[str, Any] = {}
    for tc_id, m_data in matrix.items():
        result_ids = m_data.get("result_ids", [])
        if result_ids:
            latest = results_by_id.get(result_ids[-1])
            if latest:
                results_by_tc[tc_id] = latest

    return dict(
        strategy=strategy,
        release=strategy.get("release", "draft"),
        cases=cases,
        matrix=matrix,
        bugs=bugs,
        results_by_tc=results_by_tc,
        total_cases=total,
        pass_count=pass_count,
        fail_count=fail_count,
        not_run=not_run,
        open_bugs=open_bugs,
        pass_rate=pass_rate,
    )


def generate_sprint(testboat_root: Path) -> Path:
    """Render sprint test report. Returns output path."""
    data = _compute_sprint_data(testboat_root)
    html = _render(_SPRINT_TMPL, **data)
    return _write_report(testboat_root, f"sprint-{data['release']}.html", html)


def generate_closure(testboat_root: Path, summary: str = "") -> Path:
    """Render closure report. Returns output path."""
    data = _compute_sprint_data(testboat_root)
    strategy = data["strategy"]
    bugs = data["bugs"]

    # Metrics check
    severity_rules = strategy.get("metrics", {}).get("severity", [])
    open_bugs_list = [b for b in bugs
                      if b.get("status") not in ("closed", "wont-fix", "deferred")]
    metrics_rows = []
    all_metrics_pass = True
    for rule in severity_rules:
        level = rule.get("level", "")
        acceptable = rule.get("acceptable", 0)
        open_count = sum(1 for b in open_bugs_list if b.get("priority") == level)
        passed = open_count <= acceptable
        if not passed:
            all_metrics_pass = False
        metrics_rows.append(dict(level=level, open=open_count,
                                 acceptable=acceptable, passed=passed))

    criteria_met = all_metrics_pass and data["pass_rate"] == 100

    if not summary:
        status = "passed" if criteria_met else "not yet ready for release"
        summary = (
            f"Release {data['release']} test closure. "
            f"{data['pass_count']}/{data['total_cases']} test cases passed "
            f"({data['pass_rate']}% pass rate). "
            f"{len(open_bugs_list)} open bug(s). "
            f"Overall status: {status}."
        )

    closed_bugs = len(bugs) - len(open_bugs_list)

    html = _render(
        _CLOSURE_TMPL,
        **data,
        closed_bugs=closed_bugs,
        metrics_rows=metrics_rows,
        criteria_met=criteria_met,
        exit_criteria=strategy.get("exit_criteria", []),
        summary=summary,
    )
    return _write_report(testboat_root, f"closure-{data['release']}.html", html)


# ---------------------------------------------------------------------------
# Index page — top-level version switcher + per-version report index
# ---------------------------------------------------------------------------

_SHARED_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
     background:#0f1117;color:#e2e8f0;min-height:100vh}
.hero{background:linear-gradient(135deg,#1e3a5f 0%,#0d47a1 50%,#1a237e 100%);
      padding:40px 40px 32px;position:relative;overflow:hidden}
.hero::before{content:'';position:absolute;top:-50%;right:-10%;width:500px;height:500px;
  border-radius:50%;background:rgba(255,255,255,.04);pointer-events:none}
.hero-inner{max-width:1100px;margin:0 auto;position:relative}
.hero-badge{display:inline-flex;align-items:center;gap:6px;
  background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.2);
  border-radius:20px;padding:4px 14px;font-size:12px;color:#93c5fd;
  margin-bottom:16px;letter-spacing:.5px;text-transform:uppercase}
.hero h1{font-size:32px;font-weight:700;color:#fff;letter-spacing:-.5px;margin-bottom:6px}
.hero p{color:#93c5fd;font-size:14px}
.hero-meta{margin-top:20px;display:flex;gap:20px;flex-wrap:wrap}
.hero-meta span{font-size:13px;color:#cbd5e1}.hero-meta strong{color:#fff}
.back-link{display:inline-flex;align-items:center;gap:6px;color:#60a5fa;
           font-size:13px;text-decoration:none;margin-bottom:12px}
.back-link:hover{color:#93c5fd}
.kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
         gap:14px;max-width:1100px;margin:28px auto 0;padding:0 40px}
.kpi{background:#1e2433;border:1px solid #2d3748;border-radius:12px;
     padding:18px;text-align:center;transition:transform .15s,border-color .15s}
.kpi:hover{transform:translateY(-2px);border-color:#3b82f6}
.kpi-num{font-size:36px;font-weight:800;line-height:1}
.kpi-label{font-size:11px;color:#94a3b8;margin-top:6px;text-transform:uppercase;letter-spacing:.8px}
.pass-col{color:#34d399}.fail-col{color:#f87171}
.neutral-col{color:#60a5fa}.warn-col{color:#fbbf24}
.section{max-width:1100px;margin:36px auto;padding:0 40px}
.section-title{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:1px;
               color:#64748b;margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid #1e2433}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}
.card{background:#1e2433;border:1px solid #2d3748;border-radius:12px;padding:22px;
      display:flex;flex-direction:column;gap:10px;
      transition:border-color .15s,box-shadow .15s}
.card:hover{border-color:#3b82f6;box-shadow:0 0 0 1px #3b82f6,0 8px 32px rgba(59,130,246,.12)}
.card-icon{width:38px;height:38px;border-radius:10px;display:flex;
           align-items:center;justify-content:center;font-size:18px;flex-shrink:0}
.icon-strategy{background:rgba(139,92,246,.15)}.icon-sprint{background:rgba(59,130,246,.15)}
.icon-closure{background:rgba(16,185,129,.15)}.icon-version{background:rgba(251,191,36,.12)}
.card-header{display:flex;align-items:center;gap:10px}
.card-title{font-size:15px;font-weight:600;color:#f1f5f9}
.card-desc{font-size:12px;color:#64748b;line-height:1.6}
.card-meta{display:flex;gap:6px;flex-wrap:wrap}
.chip{background:#0f1117;border:1px solid #2d3748;border-radius:5px;
      padding:1px 7px;font-size:11px;color:#94a3b8}
.chip-pass{background:rgba(52,211,153,.1);border-color:#065f46;color:#34d399}
.chip-warn{background:rgba(251,191,36,.1);border-color:#78350f;color:#fbbf24}
.chip-draft{background:rgba(96,165,250,.1);border-color:#1e40af;color:#60a5fa}
.card-footer{margin-top:auto;padding-top:10px;display:flex;gap:8px}
.btn{display:inline-flex;align-items:center;gap:5px;background:#2563eb;color:#fff;
     border-radius:8px;padding:7px 14px;font-size:12px;font-weight:500;
     text-decoration:none;transition:background .15s}
.btn:hover{background:#1d4ed8}
.btn-ghost{background:transparent;border:1px solid #3b82f6;color:#60a5fa}
.btn-ghost:hover{background:rgba(59,130,246,.1)}
.banner{max-width:1100px;margin:0 auto;padding:0 40px}
.banner-inner{border-radius:10px;padding:14px 20px;display:flex;align-items:center;gap:14px}
.banner-icon{font-size:20px}
.banner-text strong{font-size:14px}.banner-text p{font-size:12px;color:#94a3b8;margin-top:1px}
.empty{color:#64748b;font-size:13px;padding:20px}
footer{text-align:center;padding:28px;font-size:11px;color:#475569;
       border-top:1px solid #1e2433;margin-top:20px}
"""

_DASH_TMPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>testboat — Test Dashboard</title>
<style>{{ css }}</style>
</head>
<body>
<div class="hero">
  <div class="hero-inner">
    <div class="hero-badge">🧪 testboat — Manage Tests Like Code</div>
    <h1>Test Dashboard</h1>
    <p>{{ ts }}</p>
  </div>
</div>

<div class="section" style="margin-top:32px">
  <div class="section-title">Versions</div>
  <div class="grid">
    {% for v in versions %}
    <div class="card">
      <div class="card-header">
        <div class="card-icon icon-version">{{ '📝' if v.name == 'draft' else '📦' }}</div>
        <div class="card-title">{{ v.name }}</div>
      </div>
      <div class="card-meta">
        <span class="chip {{ 'chip-draft' if v.name == 'draft' else '' }}">{{ v.name }}</span>
        {% if v.base %}<span class="chip">based on {{ v.base }}</span>{% endif %}
        <span class="chip">{{ v.cases }} TCs</span>
        <span class="chip {{ 'chip-pass' if v.pass_rate == 100 else 'chip-warn' if v.pass_rate >= 80 else '' }}">{{ v.pass_rate }}% pass</span>
        {% if v.open_bugs > 0 %}<span class="chip" style="border-color:#7f1d1d;color:#f87171">{{ v.open_bugs }} open bugs</span>{% endif %}
        {% if v.created_at %}<span class="chip">{{ v.created_at[:10] }}</span>{% endif %}
      </div>
      <div class="card-footer">
        {% if v.has_reports %}
        <a href="{{ v.reports_url }}" class="btn">View Reports →</a>
        {% else %}
        <span class="btn btn-ghost" style="opacity:.5;cursor:default">No reports yet</span>
        {% endif %}
      </div>
    </div>
    {% endfor %}
    {% if not versions %}
    <div class="empty">No versions found. Run <code>testboat init</code> first.</div>
    {% endif %}
  </div>
</div>

<footer>Generated by <strong>testboat</strong> · {{ ts }}</footer>
</body>
</html>"""

_INDEX_TMPL = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>testboat Reports — {{ release }}</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
     background:#0f1117;color:#e2e8f0;min-height:100vh}

/* Hero header */
.hero{background:linear-gradient(135deg,#1e3a5f 0%,#0d47a1 50%,#1a237e 100%);
      padding:48px 40px 36px;position:relative;overflow:hidden}
.hero::before{content:'';position:absolute;top:-50%;right:-10%;
  width:500px;height:500px;border-radius:50%;
  background:rgba(255,255,255,0.04);pointer-events:none}
.hero-inner{max-width:1100px;margin:0 auto;position:relative}
.hero-badge{display:inline-flex;align-items:center;gap:6px;
  background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.2);
  border-radius:20px;padding:4px 14px;font-size:12px;color:#93c5fd;
  margin-bottom:20px;letter-spacing:.5px;text-transform:uppercase}
.hero h1{font-size:36px;font-weight:700;color:#fff;letter-spacing:-0.5px;
         margin-bottom:8px}
.hero p{color:#93c5fd;font-size:15px}
.hero-meta{margin-top:24px;display:flex;gap:24px;flex-wrap:wrap}
.hero-meta span{font-size:13px;color:#cbd5e1}
.hero-meta strong{color:#fff}

/* KPI cards */
.kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
         gap:16px;max-width:1100px;margin:32px auto 0;padding:0 40px}
.kpi{background:#1e2433;border:1px solid #2d3748;border-radius:12px;
     padding:20px;text-align:center;transition:transform .15s,border-color .15s}
.kpi:hover{transform:translateY(-2px);border-color:#3b82f6}
.kpi-num{font-size:40px;font-weight:800;line-height:1}
.kpi-label{font-size:12px;color:#94a3b8;margin-top:6px;text-transform:uppercase;
            letter-spacing:.8px}
.pass-col{color:#34d399}.fail-col{color:#f87171}
.neutral-col{color:#60a5fa}.warn-col{color:#fbbf24}

/* Reports section */
.section{max-width:1100px;margin:40px auto;padding:0 40px}
.section-title{font-size:13px;font-weight:600;text-transform:uppercase;
               letter-spacing:1px;color:#64748b;margin-bottom:16px;
               padding-bottom:8px;border-bottom:1px solid #1e2433}

.report-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));
             gap:16px}
.report-card{background:#1e2433;border:1px solid #2d3748;border-radius:12px;
             padding:24px;display:flex;flex-direction:column;gap:12px;
             transition:border-color .15s,box-shadow .15s}
.report-card:hover{border-color:#3b82f6;
                   box-shadow:0 0 0 1px #3b82f6,0 8px 32px rgba(59,130,246,.15)}
.card-icon{width:40px;height:40px;border-radius:10px;display:flex;
           align-items:center;justify-content:center;font-size:20px;flex-shrink:0}
.icon-strategy{background:rgba(139,92,246,.15)}
.icon-sprint{background:rgba(59,130,246,.15)}
.icon-closure{background:rgba(16,185,129,.15)}
.card-header{display:flex;align-items:center;gap:12px}
.card-title{font-size:16px;font-weight:600;color:#f1f5f9}
.card-desc{font-size:13px;color:#64748b;line-height:1.6}
.card-meta{display:flex;gap:8px;flex-wrap:wrap}
.chip{background:#0f1117;border:1px solid #2d3748;border-radius:6px;
      padding:2px 8px;font-size:11px;color:#94a3b8}
.card-footer{margin-top:auto;padding-top:12px}
.btn{display:inline-flex;align-items:center;gap:6px;
     background:#2563eb;color:#fff;border-radius:8px;
     padding:8px 16px;font-size:13px;font-weight:500;
     text-decoration:none;transition:background .15s}
.btn:hover{background:#1d4ed8}
.btn-ghost{background:transparent;border:1px solid #3b82f6;color:#60a5fa}
.btn-ghost:hover{background:rgba(59,130,246,.1)}

/* Status banner */
.banner{max-width:1100px;margin:0 auto 0;padding:0 40px}
.banner-inner{background:{% if ready %}rgba(16,185,129,.1){% else %}rgba(239,68,68,.1){% endif %};
  border:1px solid {% if ready %}#065f46{% else %}#7f1d1d{% endif %};
  border-radius:12px;padding:16px 24px;display:flex;align-items:center;gap:16px}
.banner-icon{font-size:24px}
.banner-text strong{font-size:15px;color:{% if ready %}#34d399{% else %}#f87171{% endif %}}
.banner-text p{font-size:13px;color:#94a3b8;margin-top:2px}

footer{text-align:center;padding:32px;font-size:12px;color:#475569;
       border-top:1px solid #1e2433;margin-top:24px}
</style>
</head>
<body>

<div class="hero">
  <div class="hero-inner">
    <div class="hero-badge">🧪 testboat — Manage Tests Like Code</div>
    <h1>Test Reports</h1>
    <p>Release <strong>{{ release }}</strong> · {{ ts }}</p>
    <div class="hero-meta">
      <span>Sprint <strong>{{ release }}</strong></span>
      <span>Pass Rate <strong>{{ pass_rate }}%</strong></span>
      <span>Open Bugs <strong>{{ open_bugs }}</strong></span>
    </div>
  </div>
</div>

<div class="kpi-row">
  <div class="kpi">
    <div class="kpi-num neutral-col">{{ total_cases }}</div>
    <div class="kpi-label">Test Cases</div>
  </div>
  <div class="kpi">
    <div class="kpi-num pass-col">{{ pass_count }}</div>
    <div class="kpi-label">Passed</div>
  </div>
  <div class="kpi">
    <div class="kpi-num fail-col">{{ fail_count }}</div>
    <div class="kpi-label">Failed</div>
  </div>
  <div class="kpi">
    <div class="kpi-num {% if pass_rate == 100 %}pass-col{% elif pass_rate >= 80 %}warn-col{% else %}fail-col{% endif %}">{{ pass_rate }}%</div>
    <div class="kpi-label">Pass Rate</div>
  </div>
  <div class="kpi">
    <div class="kpi-num {% if open_bugs == 0 %}pass-col{% else %}fail-col{% endif %}">{{ open_bugs }}</div>
    <div class="kpi-label">Open Bugs</div>
  </div>
  <div class="kpi">
    <div class="kpi-num neutral-col">{{ total_bugs }}</div>
    <div class="kpi-label">Total Bugs</div>
  </div>
</div>

<div class="banner" style="margin-top:32px">
  <div class="banner-inner">
    <div class="banner-icon">{% if ready %}✅{% else %}⚠️{% endif %}</div>
    <div class="banner-text">
      <strong>{% if ready %}READY FOR RELEASE{% else %}NOT READY — Issues remain{% endif %}</strong>
      <p>P0/P1 open bugs: {{ open_p0 + open_p1 }} · TC pass rate: {{ pass_rate }}%{% if ready %} · All exit criteria met{% endif %}</p>
    </div>
  </div>
</div>

<div class="section">
  <div class="section-title">Available Reports</div>
  <div class="report-grid">

    {% for r in reports %}
    <div class="report-card">
      <div class="card-header">
        <div class="card-icon icon-{{ r.type }}">{{ r.icon }}</div>
        <div class="card-title">{{ r.title }}</div>
      </div>
      <div class="card-desc">{{ r.desc }}</div>
      <div class="card-meta">
        {% for chip in r.chips %}
        <span class="chip">{{ chip }}</span>
        {% endfor %}
      </div>
      <div class="card-footer">
        <a href="{{ r.filename }}" class="btn">Open Report →</a>
      </div>
    </div>
    {% endfor %}

    {% if not reports %}
    <div style="color:#64748b;font-size:14px;padding:24px">
      No reports generated yet. Run <code>testboat report strategy</code>,
      <code>testboat report sprint</code>, or <code>testboat report closure</code>.
    </div>
    {% endif %}

  </div>
</div>

<footer>Generated by <strong>testboat</strong> · {{ ts }}</footer>
</body>
</html>"""


def _version_stats(version_dir: Path) -> dict:
    """Compute summary stats for a version directory."""
    cases_dir = version_dir / "cases"
    bugs_dir = version_dir / "bugs"
    cases = list(cases_dir.glob("TC-*.yaml")) if cases_dir.exists() else []
    bugs_raw = [yaml.safe_load(p.read_text(encoding="utf-8"))
                for p in sorted(bugs_dir.glob("BUG-*.yaml"))] if bugs_dir.exists() else []

    # Load execution matrix to get actual pass/fail results
    matrix_path = version_dir / "executions" / "execution-matrix.yaml"
    matrix: dict = yaml.safe_load(matrix_path.read_text(encoding="utf-8")) \
        if matrix_path.exists() else {}

    total = len(cases)
    pass_count = 0
    for p in cases:
        d = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        tc_id = d.get("id", "")
        if matrix.get(tc_id, {}).get("latest_status") == "pass":
            pass_count += 1

    open_bugs = sum(1 for b in bugs_raw
                    if b.get("status") not in ("closed", "wont-fix", "deferred"))
    pass_rate = round(pass_count / total * 100) if total else 0
    return dict(cases=total, pass_rate=pass_rate, open_bugs=open_bugs)


def _per_version_report_index(testboat_root: Path, version_name: str,
                               version_dir: Path, reports_dir: Path) -> Path:
    """Generate reports/index.html for one version. Returns path."""
    stats = _version_stats(version_dir)
    # Load execution matrix for accurate pass/fail counts
    matrix_path = version_dir / "executions" / "execution-matrix.yaml"
    matrix_data: dict = yaml.safe_load(matrix_path.read_text(encoding="utf-8")) \
        if matrix_path.exists() else {}
    bugs_raw = [yaml.safe_load(p.read_text(encoding="utf-8"))
                for p in sorted((version_dir / "bugs").glob("BUG-*.yaml"))]  \
        if (version_dir / "bugs").exists() else []
    open_bugs_list = [b for b in bugs_raw
                      if b.get("status") not in ("closed", "wont-fix", "deferred")]
    open_p0 = sum(1 for b in open_bugs_list if b.get("priority") == "P0")
    open_p1 = sum(1 for b in open_bugs_list if b.get("priority") == "P1")

    strategy_path = version_dir / "strategy.yaml"
    strategy = yaml.safe_load(strategy_path.read_text(encoding="utf-8")) \
        if strategy_path.exists() else {}
    severity_rules = strategy.get("metrics", {}).get("severity", [])
    all_metrics_pass = True
    for rule in severity_rules:
        level, acceptable = rule.get("level", ""), rule.get("acceptable", 0)
        if sum(1 for b in open_bugs_list if b.get("priority") == level) > acceptable:
            all_metrics_pass = False
    ready = all_metrics_pass and stats["pass_rate"] == 100

    report_meta = {
        "strategy": dict(type="strategy", icon="📋", title="Test Strategy",
                         desc="Risk matrix, scope, test pyramid, entry/exit criteria.",
                         chips=["Strategy", "Risk-Based"]),
        "sprint": dict(type="sprint", icon="🧪", title="Sprint Test Report",
                       desc=f"{stats['cases']} test cases · {stats['pass_rate']}% pass rate.",
                       chips=["Cases", "Execution", "Bugs"]),
        "closure": dict(type="closure", icon="📊", title="Test Closure Report",
                        desc="Metrics vs exit criteria · Sign-off status.",
                        chips=["Metrics", "Sign-off", "Summary"]),
    }
    available_reports = []
    if reports_dir.exists():
        for html_file in sorted(reports_dir.glob("*.html")):
            if html_file.name == "index.html":
                continue
            for key, meta in report_meta.items():
                if html_file.name.startswith(key):
                    available_reports.append(dict(**meta, filename=html_file.name))
                    break

    env = Environment(loader=BaseLoader())
    tmpl = env.from_string(_INDEX_TMPL)
    html = tmpl.render(
        css=_SHARED_CSS, ts=_TIMESTAMP,
        release=version_name,
        total_cases=stats["cases"],
        pass_count=sum(1 for p in (version_dir / "cases").glob("TC-*.yaml")
                       if matrix_data.get(
                           yaml.safe_load(p.read_text(encoding="utf-8")).get("id"), {}
                       ).get("latest_status") == "pass")
                   if (version_dir / "cases").exists() else 0,
        fail_count=sum(1 for p in (version_dir / "cases").glob("TC-*.yaml")
                       if matrix_data.get(
                           yaml.safe_load(p.read_text(encoding="utf-8")).get("id"), {}
                       ).get("latest_status") == "fail")
                   if (version_dir / "cases").exists() else 0,
        pass_rate=stats["pass_rate"],
        open_bugs=len(open_bugs_list),
        total_bugs=len(bugs_raw),
        open_p0=open_p0, open_p1=open_p1,
        ready=ready,
        reports=available_reports,
    )
    reports_dir.mkdir(parents=True, exist_ok=True)
    out = reports_dir / "index.html"
    out.write_text(html, encoding="utf-8")
    return out


def generate_index(testboat_root: Path) -> Path:
    """Generate top-level dashboard (version switcher) at .testboat/index.html.

    Also generates per-version reports/index.html for draft and all named versions.
    Returns the top-level index path.
    """
    testboat_dir = testboat_root / ".testboat"
    testboat_dir.mkdir(parents=True, exist_ok=True)

    # Collect all versions: draft + named
    all_versions: list[dict] = []

    draft_dir = testboat_dir / "draft"
    if draft_dir.exists():
        stats = _version_stats(draft_dir)
        reports_dir = draft_dir / "reports"
        _per_version_report_index(testboat_root, "draft", draft_dir, reports_dir)
        all_versions.append(dict(
            name="draft",
            base=None,
            created_at="",
            has_reports=bool(list(reports_dir.glob("*.html")) if reports_dir.exists() else []),
            reports_url="draft/reports/index.html",
            **stats,
        ))

    from testboat.commands.version import _list_versions, _read_meta, _version_path
    for vname in _list_versions(testboat_root):
        vdir = _version_path(testboat_root, vname)
        meta = _read_meta(vdir)
        stats = _version_stats(vdir)
        reports_dir = vdir / "reports"
        _per_version_report_index(testboat_root, vname, vdir, reports_dir)
        all_versions.append(dict(
            name=vname,
            base=meta.get("base"),
            created_at=meta.get("created_at", ""),
            has_reports=bool(list(reports_dir.glob("*.html")) if reports_dir.exists() else []),
            reports_url=f"{vname}/reports/index.html",
            **stats,
        ))

    env = Environment(loader=BaseLoader())
    tmpl = env.from_string(_DASH_TMPL)
    html = tmpl.render(css=_SHARED_CSS, ts=_TIMESTAMP, versions=all_versions)

    out = testboat_dir / "index.html"
    out.write_text(html, encoding="utf-8")
    return out
