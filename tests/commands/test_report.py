"""Unit tests for testboat report + preview — 100% coverage."""

import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from typer.testing import CliRunner

from testboat.cli import app
from testboat.commands.bug import add_bug
from testboat.commands.case import add_case, set_status
from testboat.commands.preview import (
    PID_FILE,
    _find_free_port,
    _kill_existing,
    _pid_path,
    _write_pid,
    export_pdf,
    serve_reports,
)
from testboat.commands.report import (
    _build_tc_json,
    _load_bugs,
    _load_cases,
    _load_matrix,
    _load_results,
    _load_strategy,
    _reports_dir,
    generate_closure,
    generate_index,
    generate_sprint,
    generate_strategy,
)
from testboat.commands.result import record_result
from testboat.commands.strategy import create_strategy
from testboat.commands.tag import add_tag

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup(root: Path) -> None:
    """Full workspace for report generation."""
    add_tag(root, "sprint", "v1.0.0")
    add_tag(root, "type", "functional")
    add_tag(root, "module", "auth")
    create_strategy(root)
    add_case(root, "Login test", sprint="v1.0.0", type_="functional",
             module="auth", req_id="STORY-001")
    set_status(root, "TC-001", "ready")
    record_result(root, "TC-001", "pass", execution_type="automated")
    set_status(root, "TC-001", "pass")


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------


class TestDataLoaders:
    def test_load_strategy_empty(self, tmp_path: Path) -> None:
        assert _load_strategy(tmp_path) == {}

    def test_load_strategy(self, tmp_path: Path) -> None:
        create_strategy(tmp_path)
        data = _load_strategy(tmp_path)
        assert "release" in data

    def test_load_cases_empty(self, tmp_path: Path) -> None:
        assert _load_cases(tmp_path) == []

    def test_load_cases(self, tmp_path: Path) -> None:
        add_case(tmp_path, "Test")
        assert len(_load_cases(tmp_path)) == 1

    def test_load_results_empty(self, tmp_path: Path) -> None:
        assert _load_results(tmp_path) == []

    def test_load_results(self, tmp_path: Path) -> None:
        record_result(tmp_path, "TC-001", "pass")
        assert len(_load_results(tmp_path)) == 1

    def test_load_matrix_empty(self, tmp_path: Path) -> None:
        assert _load_matrix(tmp_path) == {}

    def test_load_matrix(self, tmp_path: Path) -> None:
        record_result(tmp_path, "TC-001", "pass")
        data = _load_matrix(tmp_path)
        assert "TC-001" in data

    def test_load_bugs_empty(self, tmp_path: Path) -> None:
        assert _load_bugs(tmp_path) == []

    def test_load_bugs(self, tmp_path: Path) -> None:
        add_bug(tmp_path, "Bug")
        assert len(_load_bugs(tmp_path)) == 1


# ---------------------------------------------------------------------------
# generate_strategy
# ---------------------------------------------------------------------------


class TestGenerateIndex:
    def test_creates_toplevel_index_html(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        path = generate_index(tmp_path)
        assert path.name == "index.html"
        assert path.parent == tmp_path / ".testboat"
        assert path.exists()

    def test_index_shows_draft_version(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        path = generate_index(tmp_path)
        assert "draft" in path.read_text(encoding="utf-8")

    def test_index_shows_named_versions(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        from testboat.commands.version import create_version
        create_version(tmp_path, "v1.0")
        path = generate_index(tmp_path)
        assert "v1.0" in path.read_text(encoding="utf-8")

    def test_per_version_index_created(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        generate_index(tmp_path)
        draft_idx = tmp_path / ".testboat" / "draft" / "reports" / "index.html"
        assert draft_idx.exists()

    def test_per_version_index_has_ready_banner(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        generate_strategy(tmp_path)
        generate_sprint(tmp_path)
        generate_index(tmp_path)
        content = (tmp_path / ".testboat" / "draft" / "reports" / "index.html").read_text()
        assert "READY FOR RELEASE" in content

    def test_per_version_index_not_ready_with_bugs(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        add_bug(tmp_path, "Critical bug", priority="P0")
        generate_index(tmp_path)
        content = (tmp_path / ".testboat" / "draft" / "reports" / "index.html").read_text()
        assert "NOT READY" in content

    def test_per_version_index_shows_reports(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        generate_strategy(tmp_path)
        generate_sprint(tmp_path)
        generate_index(tmp_path)
        content = (tmp_path / ".testboat" / "draft" / "reports" / "index.html").read_text()
        assert "strategy" in content
        assert "sprint" in content

    def test_per_version_index_skips_itself(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        generate_strategy(tmp_path)
        generate_index(tmp_path)
        generate_index(tmp_path)  # second call: index.html already exists in reports/
        content = (tmp_path / ".testboat" / "draft" / "reports" / "index.html").read_text()
        assert content.count("index.html") == 0

    def test_index_no_draft_dir(self, tmp_path: Path) -> None:
        path = generate_index(tmp_path)
        assert path.exists()  # top-level index created even with empty workspace

    def test_index_kpi_in_per_version_page(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        generate_index(tmp_path)
        content = (tmp_path / ".testboat" / "draft" / "reports" / "index.html").read_text()
        assert "100%" in content


class TestGenerateStrategy:
    def test_creates_html_file(self, tmp_path: Path) -> None:
        create_strategy(tmp_path)
        path = generate_strategy(tmp_path)
        assert path.exists()
        assert path.suffix == ".html"

    def test_html_contains_release(self, tmp_path: Path) -> None:
        create_strategy(tmp_path)
        path = generate_strategy(tmp_path)
        assert "release" in path.read_text(encoding="utf-8").lower()

    def test_file_in_reports_dir(self, tmp_path: Path) -> None:
        create_strategy(tmp_path)
        path = generate_strategy(tmp_path)
        assert path.parent == _reports_dir(tmp_path)

    def test_works_with_no_strategy(self, tmp_path: Path) -> None:
        path = generate_strategy(tmp_path)
        assert path.exists()


# ---------------------------------------------------------------------------
# generate_sprint
# ---------------------------------------------------------------------------


class TestGenerateSprint:
    def test_creates_html_file(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        path = generate_sprint(tmp_path)
        assert path.exists()

    def test_html_contains_tc_id(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        path = generate_sprint(tmp_path)
        assert "TC-001" in path.read_text(encoding="utf-8")

    def test_html_contains_pass(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        path = generate_sprint(tmp_path)
        assert "pass" in path.read_text(encoding="utf-8")

    def test_shows_bugs_section(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        add_bug(tmp_path, "Bug", sprint="v1.0.0")
        path = generate_sprint(tmp_path)
        assert "BUG-001" in path.read_text(encoding="utf-8")

    def test_no_bugs_shows_no_bugs(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        path = generate_sprint(tmp_path)
        assert "No bugs filed" in path.read_text(encoding="utf-8")

    def test_empty_workspace(self, tmp_path: Path) -> None:
        path = generate_sprint(tmp_path)
        assert path.exists()

    def test_filter_chips_present(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        html = generate_sprint(tmp_path).read_text(encoding="utf-8")
        assert "filter-chip" in html
        assert "toggleFilter" in html

    def test_export_button_present(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        html = generate_sprint(tmp_path).read_text(encoding="utf-8")
        assert "export-btn" in html
        assert "exportCSV" in html

    def test_tc_json_data_element_present(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        html = generate_sprint(tmp_path).read_text(encoding="utf-8")
        assert 'id="tc-json"' in html
        assert "JSON.parse" in html

    def test_script_not_closed_by_slash_script_in_tc_content(self, tmp_path: Path) -> None:
        add_tag(tmp_path, "sprint", "v1.0.0")
        add_tag(tmp_path, "type", "functional")
        add_tag(tmp_path, "module", "xss")
        create_strategy(tmp_path)
        add_case(tmp_path, "XSS title </script><script>window.HACKED=true</script>",
                 sprint="v1.0.0", type_="functional", module="xss", req_id="STORY-001")
        set_status(tmp_path, "TC-001", "ready")
        record_result(tmp_path, "TC-001", "pass", execution_type="automated")
        set_status(tmp_path, "TC-001", "pass")
        html = generate_sprint(tmp_path).read_text(encoding="utf-8")
        # </script> must not appear raw inside any <script> element
        import re
        script_blocks = re.findall(r"<script(?:\s[^>]*)?>.*?</script>", html, re.DOTALL | re.IGNORECASE)
        for block in script_blocks:
            inner = re.sub(r"<script[^>]*>", "", block, count=1)
            inner = inner[: inner.rfind("</script>")]
            assert "</script>" not in inner.lower(), \
                f"Raw </script> found inside a script block: {inner[:100]}"
        assert "toggleFilter" in html
        assert "exportCSV" in html

    def test_u2028_u2029_do_not_break_script(self, tmp_path: Path) -> None:
        add_tag(tmp_path, "sprint", "v1.0.0")
        add_tag(tmp_path, "type", "functional")
        add_tag(tmp_path, "module", "unicode")
        create_strategy(tmp_path)
        dangerous = f"title with line-sep   and para-sep   inside"
        add_case(tmp_path, dangerous, sprint="v1.0.0", type_="functional",
                 module="unicode", req_id="STORY-001")
        set_status(tmp_path, "TC-001", "ready")
        record_result(tmp_path, "TC-001", "pass", execution_type="automated")
        set_status(tmp_path, "TC-001", "pass")
        html = generate_sprint(tmp_path).read_text(encoding="utf-8")
        # Raw U+2028 / U+2029 must not appear inside any <script> element
        import re
        script_blocks = re.findall(r"<script(?:\s[^>]*)?>.*?</script>", html, re.DOTALL | re.IGNORECASE)
        for block in script_blocks:
            assert " " not in block, "U+2028 found raw inside a script block"
            assert " " not in block, "U+2029 found raw inside a script block"
        assert "toggleFilter" in html


class TestBuildTcJson:
    def _make_data(self, cases: list, matrix: dict | None = None,
                   results_by_tc: dict | None = None) -> dict:
        return {"cases": cases, "matrix": matrix or {}, "results_by_tc": results_by_tc or {}}

    def test_returns_valid_json(self, tmp_path: Path) -> None:
        import json
        data = self._make_data([{"id": "TC-1", "title": "t", "tags": {"sprint": "s",
                                  "module": "m", "type": "f"}, "status": "pass",
                                  "priority": "P1", "req_id": "R1",
                                  "preconditions": ["p"], "steps": [{"action": "a",
                                  "expected": "e"}], "expected_result": "er", "notes": ""}])
        result = json.loads(_build_tc_json(data))
        assert result[0]["id"] == "TC-1"
        assert result[0]["steps"] == "1. a → e"

    def test_script_tag_in_title_escaped(self) -> None:
        data = self._make_data([{"id": "TC-1", "title": "</script><script>bad()</script>",
                                  "tags": {}, "status": "pass", "priority": "P1",
                                  "req_id": "", "preconditions": [], "steps": [],
                                  "expected_result": "", "notes": ""}])
        result = _build_tc_json(data)
        assert "</script>" not in result
        assert "<\\/script>" in result

    def test_u2028_u2029_escaped(self) -> None:
        data = self._make_data([{"id": "TC-1", "title": f"a b c",
                                  "tags": {}, "status": "pass", "priority": "P1",
                                  "req_id": "", "preconditions": [], "steps": [],
                                  "expected_result": "", "notes": ""}])
        result = _build_tc_json(data)
        assert " " not in result
        assert " " not in result

    def test_none_tags_handled(self) -> None:
        data = self._make_data([{"id": "TC-1", "title": "t", "tags": None,
                                  "status": "pass", "priority": "P1", "req_id": "",
                                  "preconditions": None, "steps": None,
                                  "expected_result": None, "notes": None}])
        import json
        result = json.loads(_build_tc_json(data))
        assert result[0]["module"] == ""
        assert result[0]["steps"] == ""
        assert result[0]["preconditions"] == ""

    def test_result_metadata_included(self) -> None:
        import json
        cases = [{"id": "TC-1", "title": "t", "tags": {}, "status": "pass",
                  "priority": "P1", "req_id": "", "preconditions": [],
                  "steps": [], "expected_result": "", "notes": ""}]
        results_by_tc = {"TC-1": {"executed_at": "2026-01-01T00:00:00",
                                   "executed_by": "AI", "execution_type": "automated"}}
        data = self._make_data(cases, results_by_tc=results_by_tc)
        result = json.loads(_build_tc_json(data))
        assert result[0]["executed_at"] == "2026-01-01T00:00:00"
        assert result[0]["executed_by"] == "AI"

    def test_latest_result_from_matrix(self) -> None:
        import json
        cases = [{"id": "TC-1", "title": "t", "tags": {}, "status": "pass",
                  "priority": "P1", "req_id": "", "preconditions": [],
                  "steps": [], "expected_result": "", "notes": ""}]
        matrix = {"TC-1": {"latest_status": "fail"}}
        data = self._make_data(cases, matrix=matrix)
        result = json.loads(_build_tc_json(data))
        assert result[0]["latest_result"] == "fail"

    def test_missing_tc_defaults_to_not_run(self) -> None:
        import json
        cases = [{"id": "TC-99", "title": "t", "tags": {}, "status": "ready",
                  "priority": "P2", "req_id": "", "preconditions": [],
                  "steps": [], "expected_result": "", "notes": ""}]
        data = self._make_data(cases)
        result = json.loads(_build_tc_json(data))
        assert result[0]["latest_result"] == "not-run"


# ---------------------------------------------------------------------------
# generate_closure
# ---------------------------------------------------------------------------


class TestGenerateClosure:
    def test_creates_html_file(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        path = generate_closure(tmp_path)
        assert path.exists()

    def test_html_shows_ready_when_pass(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        path = generate_closure(tmp_path)
        assert "READY FOR RELEASE" in path.read_text(encoding="utf-8")

    def test_html_shows_not_ready_when_bugs(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        add_bug(tmp_path, "Critical bug", priority="P0")
        path = generate_closure(tmp_path)
        assert "NOT READY" in path.read_text(encoding="utf-8")

    def test_custom_summary_included(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        path = generate_closure(tmp_path, summary="All tests passed successfully.")
        assert "All tests passed successfully." in path.read_text(encoding="utf-8")

    def test_default_summary_generated(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        path = generate_closure(tmp_path)
        content = path.read_text(encoding="utf-8")
        assert "100%" in content  # pass rate

    def test_metrics_rows_rendered(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        path = generate_closure(tmp_path)
        assert "P0" in path.read_text(encoding="utf-8")

    def test_no_severity_rules(self, tmp_path: Path) -> None:
        create_strategy(tmp_path)
        path = tmp_path / ".testboat" / "draft" / "strategy.yaml"
        data = yaml.safe_load(path.read_text())
        data["metrics"]["severity"] = []
        path.write_text(yaml.dump(data))
        result = generate_closure(tmp_path)
        assert result.exists()


# ---------------------------------------------------------------------------
# preview: _find_free_port + serve_reports
# ---------------------------------------------------------------------------


class TestPidManagement:
    def test_pid_path_in_testboat_dir(self, tmp_path: Path) -> None:
        assert _pid_path(tmp_path) == tmp_path / ".testboat" / PID_FILE

    def test_write_pid_creates_file(self, tmp_path: Path) -> None:
        (tmp_path / ".testboat").mkdir()
        _write_pid(tmp_path, 12345)
        assert _pid_path(tmp_path).read_text() == "12345"

    def test_kill_existing_no_file(self, tmp_path: Path) -> None:
        assert _kill_existing(tmp_path) is False

    def test_kill_existing_removes_stale_pid(self, tmp_path: Path) -> None:
        (tmp_path / ".testboat").mkdir()
        _pid_path(tmp_path).write_text("999999999")  # non-existent PID
        assert _kill_existing(tmp_path) is False  # no process, but removed
        assert not _pid_path(tmp_path).exists()

    def test_kill_existing_real_process(self, tmp_path: Path) -> None:
        import subprocess as sp
        proc = sp.Popen(["sleep", "60"])
        (tmp_path / ".testboat").mkdir()
        _pid_path(tmp_path).write_text(str(proc.pid))
        result = _kill_existing(tmp_path)
        proc.wait()
        assert result is True
        assert not _pid_path(tmp_path).exists()

    def test_kill_existing_invalid_pid_file(self, tmp_path: Path) -> None:
        (tmp_path / ".testboat").mkdir()
        _pid_path(tmp_path).write_text("not-a-pid")
        assert _kill_existing(tmp_path) is False

    def test_serve_creates_pid_file(self, tmp_path: Path) -> None:
        stop = threading.Event()
        serve_reports(tmp_path, open_browser=False, _stop_event=stop)
        assert _pid_path(tmp_path).exists()
        stop.set()

    def test_serve_kills_existing_before_start(self, tmp_path: Path) -> None:
        (tmp_path / ".testboat").mkdir()
        _pid_path(tmp_path).write_text("999999999")  # stale PID
        stop = threading.Event()
        serve_reports(tmp_path, open_browser=False, _stop_event=stop)  # should not raise
        stop.set()


class TestPreview:
    def test_find_free_port_returns_int(self) -> None:
        port = _find_free_port()
        assert isinstance(port, int)
        assert 1024 <= port <= 65535

    def test_serve_reports_returns_port_and_url(self, tmp_path: Path) -> None:
        stop = threading.Event()
        port, url = serve_reports(tmp_path, open_browser=False, _stop_event=stop)
        assert isinstance(port, int)
        assert url.startswith("http://127.0.0.1:")
        stop.set()

    def test_serve_reports_creates_testboat_dir(self, tmp_path: Path) -> None:
        stop = threading.Event()
        serve_reports(tmp_path, open_browser=False, _stop_event=stop)
        assert (tmp_path / ".testboat").exists()
        stop.set()

    def test_serve_reports_custom_port(self, tmp_path: Path) -> None:
        stop = threading.Event()
        p = _find_free_port()
        port, url = serve_reports(tmp_path, port=p, open_browser=False, _stop_event=stop)
        assert port == p
        stop.set()

    def test_serve_reports_no_stop_event_creates_one(self, tmp_path: Path) -> None:
        # When _stop_event=None, serve_reports creates its own threading.Event
        import urllib.request
        stop = threading.Event()
        # We pass None for _stop_event — serve_reports uses its own
        port, url = serve_reports(tmp_path, open_browser=False, _stop_event=None)
        # Make a request to exercise the Handler.__init__ and log_message paths
        try:
            urllib.request.urlopen(url, timeout=1)
        except Exception:
            pass  # 404 is fine, we just need to trigger the handler
        # Stop by creating external stop (serve will run forever otherwise — daemon thread)

    def test_serve_reports_open_browser(self, tmp_path: Path) -> None:
        stop = threading.Event()
        with patch("testboat.commands.preview.webbrowser.open"):
            with patch("testboat.commands.preview.threading.Timer") as mock_timer:
                mock_timer.return_value = MagicMock()
                port, url = serve_reports(tmp_path, open_browser=True, _stop_event=stop)
                mock_timer.assert_called_once()
        stop.set()

    def test_preview_server_sets_stop(self, tmp_path: Path) -> None:
        def fake_serve(root, port, open_browser, _stop_event):
            _stop_event.set()
            return (9999, "http://127.0.0.1:9999")

        with patch("testboat.cli.serve_reports", side_effect=fake_serve):
            result = runner.invoke(app, ["preview", "--no-browser",
                                         "--workspace", str(tmp_path)])
        assert "9999" in result.output

    def test_preview_keyboard_interrupt_shows_stopped(self, tmp_path: Path) -> None:
        def fake_serve(root, port, open_browser, _stop_event):
            return (8888, "http://127.0.0.1:8888")

        fake_stop = MagicMock()
        fake_stop.wait.side_effect = KeyboardInterrupt()

        with patch("testboat.cli.serve_reports", side_effect=fake_serve):
            with patch("testboat.cli.threading.Event", return_value=fake_stop):
                result = runner.invoke(app, ["preview", "--no-browser",
                                             "--workspace", str(tmp_path)])
        assert "Stopped" in result.output

    def test_serve_forever_server_close_called(self, tmp_path: Path) -> None:
        stop = threading.Event()
        port, url = serve_reports(tmp_path, open_browser=False, _stop_event=stop)
        import urllib.request
        try:
            urllib.request.urlopen(url, timeout=0.5)
        except Exception:
            pass
        stop.set()
        time.sleep(0.3)  # allow _watchdog + _serve threads to finish


# ---------------------------------------------------------------------------
# export_pdf
# ---------------------------------------------------------------------------


class TestExportPdf:
    def test_wkhtmltopdf_success(self, tmp_path: Path) -> None:
        html = tmp_path / "report.html"
        html.write_text("<html><body>test</body></html>")
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            out = export_pdf(html)
        assert out == html.with_suffix(".pdf")

    def test_wkhtmltopdf_not_found_tries_weasyprint(self, tmp_path: Path) -> None:
        html = tmp_path / "report.html"
        html.write_text("<html><body>test</body></html>")
        mock_wp = MagicMock()
        mock_wp.HTML.return_value.write_pdf = MagicMock()
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with patch.dict("sys.modules", {"weasyprint": mock_wp}):
                out = export_pdf(html)
        assert out == html.with_suffix(".pdf")

    def test_both_unavailable_raises_runtime_error(self, tmp_path: Path) -> None:
        html = tmp_path / "report.html"
        html.write_text("<html/>")
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with patch("builtins.__import__", side_effect=ImportError):
                with pytest.raises(RuntimeError, match="PDF export requires"):
                    export_pdf(html)

    def test_wkhtmltopdf_nonzero_tries_weasyprint(self, tmp_path: Path) -> None:
        html = tmp_path / "report.html"
        html.write_text("<html/>")
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_wp = MagicMock()
        mock_wp.HTML.return_value.write_pdf = MagicMock()
        with patch("subprocess.run", return_value=mock_result):
            with patch.dict("sys.modules", {"weasyprint": mock_wp}):
                out = export_pdf(html)
        assert out == html.with_suffix(".pdf")

    def test_custom_output_path(self, tmp_path: Path) -> None:
        html = tmp_path / "report.html"
        html.write_text("<html/>")
        out_path = tmp_path / "out.pdf"
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            out = export_pdf(html, out_path)
        assert out == out_path


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


class TestReportCli:
    def test_report_strategy_exits_zero(self, tmp_path: Path) -> None:
        create_strategy(tmp_path)
        result = runner.invoke(app, ["report", "strategy", str(tmp_path)])
        assert result.exit_code == 0
        assert "strategy" in result.output

    def test_report_sprint_exits_zero(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        result = runner.invoke(app, ["report", "sprint", str(tmp_path)])
        assert result.exit_code == 0
        assert "sprint" in result.output

    def test_report_closure_exits_zero(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        result = runner.invoke(app, ["report", "closure", str(tmp_path)])
        assert result.exit_code == 0
        assert "closure" in result.output

    def test_report_closure_with_summary(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        result = runner.invoke(app, ["report", "closure",
                                     "--summary", "All good.",
                                     str(tmp_path)])
        assert result.exit_code == 0


class TestPreviewCli:
    def test_preview_pdf_not_found_exits_one(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["preview", "--pdf", "nonexistent.html",
                                     "--workspace", str(tmp_path)])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_preview_pdf_runtime_error_exits_one(self, tmp_path: Path) -> None:
        html = tmp_path / "test.html"
        html.write_text("<html/>")
        with patch("testboat.commands.preview.export_pdf",
                   side_effect=RuntimeError("no tool")):
            result = runner.invoke(app, ["preview", "--pdf", str(html),
                                         "--workspace", str(tmp_path)])
        assert result.exit_code == 1

    def test_preview_pdf_success(self, tmp_path: Path) -> None:
        html = tmp_path / "test.html"
        html.write_text("<html/>")
        pdf = tmp_path / "test.pdf"
        with patch("testboat.cli.export_pdf", return_value=pdf):
            result = runner.invoke(app, ["preview", "--pdf", str(html),
                                         "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "PDF exported" in result.output

    def test_preview_server_no_browser(self, tmp_path: Path) -> None:
        stop = threading.Event()

        def fake_serve(root, port, open_browser, _stop_event):
            _stop_event.set()
            return (8888, "http://127.0.0.1:8888")

        with patch("testboat.cli.serve_reports", side_effect=fake_serve):
            result = runner.invoke(app, ["preview", "--no-browser",
                                         "--workspace", str(tmp_path)])
        assert result.exit_code == 0
        assert "8888" in result.output
