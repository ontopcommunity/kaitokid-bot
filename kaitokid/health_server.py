"""Minimal HTTP health server for Render free web service.

Render free web services must bind to $PORT or the deploy fails
("no open ports"). KaitoKid is a Pyrogram bot (long polling) and serves
no HTTP by itself, so this tiny server listens on $PORT (default 10000)
in a daemon thread and answers 200 OK to any request. It is only a
health/keep-alive endpoint; it does not serve bot traffic.

Started from kaitokid/__main__.py before the bot starts.
"""

import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from logging import getLogger

LOGGER = getLogger("KaitoKid")


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - http.server naming
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"KaitoKid OK")

    def do_HEAD(self):  # noqa: N802 - http.server naming
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()

    def log_message(self, *args):  # silence default access log
        pass


def start_health_server():
    """Start the health server in a daemon thread. No-op if PORT unset."""
    port = int(os.environ.get("PORT", "10000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    LOGGER.info("[INFO]: Health server listening on 0.0.0.0:%s", port)
    return server
