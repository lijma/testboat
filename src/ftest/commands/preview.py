"""ftest preview — serve reports locally and optionally export PDF."""

from __future__ import annotations

import http.server
import os
import signal
import socket
import subprocess
import threading
import webbrowser
from pathlib import Path

PID_FILE = ".preview.pid"


def _pid_path(ftest_root: Path) -> Path:
    return ftest_root / ".ftest" / PID_FILE


def _kill_existing(ftest_root: Path) -> bool:
    """Kill any existing preview process. Returns True if a process was killed."""
    pid_file = _pid_path(ftest_root)
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        pid_file.unlink(missing_ok=True)
        return True
    except (ProcessLookupError, ValueError):
        pid_file.unlink(missing_ok=True)
        return False


def _write_pid(ftest_root: Path, pid: int) -> None:
    _pid_path(ftest_root).write_text(str(pid))


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _make_handler(serve_dir: Path):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(serve_dir), **kwargs)

        def log_message(self, fmt: str, *args) -> None:
            pass  # suppress default logging

    return Handler


def serve_reports(
    ftest_root: Path,
    port: int | None = None,
    open_browser: bool = True,
    _stop_event: threading.Event | None = None,
) -> tuple[int, str]:
    """Kill any existing preview, then start a new HTTP server.

    Returns (port, url).
    """
    from ftest.commands.report import generate_index
    _kill_existing(ftest_root)
    generate_index(ftest_root)

    serve_dir = ftest_root / ".ftest"
    serve_dir.mkdir(parents=True, exist_ok=True)

    chosen_port = port or _find_free_port()
    handler = _make_handler(serve_dir)
    server = http.server.HTTPServer(("127.0.0.1", chosen_port), handler)
    url = f"http://127.0.0.1:{chosen_port}"

    _write_pid(ftest_root, os.getpid())

    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    stop = _stop_event or threading.Event()

    def _serve():
        server.serve_forever()
        server.server_close()

    def _watchdog():
        stop.wait()
        server.shutdown()
        _pid_path(ftest_root).unlink(missing_ok=True)

    threading.Thread(target=_serve, daemon=True).start()
    threading.Thread(target=_watchdog, daemon=True).start()
    return chosen_port, url


def export_pdf(html_path: Path, out_path: Path | None = None) -> Path:
    """Export an HTML report to PDF.

    Tries wkhtmltopdf first, then weasyprint, then raises RuntimeError.
    Returns the PDF path.
    """
    target = out_path or html_path.with_suffix(".pdf")

    try:
        result = subprocess.run(
            ["wkhtmltopdf", "--quiet", str(html_path), str(target)],
            capture_output=True,
        )
        if result.returncode == 0:
            return target
    except FileNotFoundError:
        pass

    try:
        import weasyprint  # type: ignore
        weasyprint.HTML(filename=str(html_path)).write_pdf(str(target))
        return target
    except ImportError:
        pass

    raise RuntimeError(
        "PDF export requires either 'wkhtmltopdf' (CLI) or 'weasyprint' (pip install weasyprint). "
        "Neither is available."
    )
