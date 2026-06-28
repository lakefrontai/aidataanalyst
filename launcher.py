"""
Desktop launcher for AI Data Analyst.

Starts the Streamlit server on a free local port,
waits until it responds, then opens a native webview window.
Killing the window stops the server cleanly.
"""

import os
import sys
import socket
import subprocess
import threading
import time
import webbrowser

# ---------------------------------------------------------------------------
# Resolve paths — works both in dev and inside a PyInstaller bundle
# ---------------------------------------------------------------------------
if getattr(sys, "frozen", False):
    # Running inside PyInstaller bundle
    BASE_DIR = sys._MEIPASS  # type: ignore[attr-defined]
    APP_PY   = os.path.join(BASE_DIR, "app.py")
    STREAMLIT = os.path.join(BASE_DIR, "streamlit_bin", "streamlit")
    if sys.platform == "win32":
        STREAMLIT += ".exe"
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_PY   = os.path.join(BASE_DIR, "app.py")
    STREAMLIT = "streamlit"   # on PATH in dev


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_server(port: int, timeout: int = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def _start_streamlit(port: int) -> subprocess.Popen:
    env = os.environ.copy()
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_SERVER_PORT"]     = str(port)
    env["STREAMLIT_SERVER_ADDRESS"]  = "127.0.0.1"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    env["STREAMLIT_THEME_BASE"]      = "light"

    cmd = [STREAMLIT, "run", APP_PY,
           "--server.port", str(port),
           "--server.address", "127.0.0.1",
           "--server.headless", "true",
           "--browser.gatherUsageStats", "false"]

    # Suppress console window on Windows
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

    return subprocess.Popen(cmd, env=env, **kwargs)


def main():
    port = _free_port()
    proc = _start_streamlit(port)
    url  = f"http://127.0.0.1:{port}"

    if not _wait_for_server(port, timeout=40):
        proc.terminate()
        print("ERROR: Streamlit failed to start.")
        sys.exit(1)

    # Try to use pywebview for a native window; fall back to browser
    try:
        import webview  # type: ignore[import]

        def on_closed():
            proc.terminate()

        window = webview.create_window(
            "AI Data Analyst",
            url,
            width=1280,
            height=820,
            min_size=(900, 600),
        )
        webview.start(on_closed)
    except ImportError:
        # pywebview not available — open in default browser instead
        webbrowser.open(url)
        try:
            proc.wait()
        except KeyboardInterrupt:
            pass
        finally:
            proc.terminate()


if __name__ == "__main__":
    main()
