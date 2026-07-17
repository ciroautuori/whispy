"""Desktop window for the Whispy Second Brain.

Mirrors the openvidia pattern: FastAPI serves the bundled single-page UI and
pywebview opens it in a native Window. No Rust, no Tauri, no Electron — just
Python. The FastAPI app runs in a background thread; the GUI runs on the main
thread.
"""

from __future__ import annotations

import argparse
import threading
import time

from .server import create_app
from .store import Store


def start_server(
    host: str = "127.0.0.1",
    port: int = 58182,
    store: Store | None = None,
    ready: threading.Event | None = None,
) -> None:
    """Launch the FastAPI app in a background daemon thread."""
    app = create_app(store=store)
    import uvicorn

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True, name="whispy-server")
    thread.start()
    if ready is not None:
        ready.set()
    return server


def open_desktop(port: int, width: int = 390, height: int = 760) -> None:
    """Open the Whispy Brain UI in a native desktop window via pywebview."""
    url = f"http://127.0.0.1:{port}"
    try:
        import webview
    except ImportError:
        import webbrowser

        webbrowser.open(url)
        return
    webview.create_window(
        "Whispy Brain",
        url,
        width=width,
        height=height,
        min_size=(360, 520),
        text_select=True,
    )
    webview.start(debug=False)


def run_cli(args: argparse.Namespace) -> int:
    """Entry point for the ``whispy brain`` subcommand."""
    store = Store()
    ready = threading.Event()
    start_server(port=args.port, store=store, ready=ready)
    ready.wait(timeout=5)
    time.sleep(0.4)  # let uvicorn settle
    open_desktop(args.port, args.width, args.height)
    return 0
