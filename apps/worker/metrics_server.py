"""A scrape target for the worker.

The worker records job counts, durations and queue depth into the same
in-process registry the API uses - but the API's registry is a different
process, so without this nothing ever exposes them. A worker whose jobs
are all dead-lettering would look exactly like a worker with nothing to
do.

Deliberately `http.server` rather than a second web framework: this
serves one path, is never public, and should not be able to fail in a way
that takes the worker down with it.
"""

from __future__ import annotations

import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from apps.backend.core.observability import render_prometheus

logger = logging.getLogger("workwell.worker.metrics")

DEFAULT_PORT = 9100


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802  (http.server's interface)
        if self.path.rstrip("/") in ("/metrics", ""):
            body = render_prometheus().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path.rstrip("/") == "/health/live":
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, *args) -> None:
        """Silence http.server's stderr logging; the app logs JSON."""


def serve(port: int = DEFAULT_PORT) -> ThreadingHTTPServer | None:
    try:
        server = ThreadingHTTPServer(("0.0.0.0", port), _Handler)
    except OSError as exc:
        # A metrics port that is already taken must not stop the worker
        # from doing its actual job.
        logger.warning("metrics server not started on port %s: %s", port, exc)
        return None

    thread = threading.Thread(target=server.serve_forever, name="metrics", daemon=True)
    thread.start()
    logger.info("worker metrics on :%s/metrics", port)
    return server
