"""Minimal HTTP health server for Render free web service.

Render free web services must bind to $PORT or the deploy fails
("no open ports"). KaitoKid is a Pyrogram bot (long polling) and serves
no HTTP by itself, so this tiny server listens on $PORT (default 10000)
in a daemon thread and answers 200 OK to any request. It is only a
health/keep-alive endpoint; it does not serve bot traffic.

Self-ping: Render free services sleep after 15 minutes without HTTP
traffic, so this module also runs a background thread that GETs the
service's own public URL every 10 minutes. That keeps the service awake
without any external pinger.

Started from kaitokid/__main__.py before the bot starts.
"""

import os
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from logging import getLogger

LOGGER = getLogger("KaitoKid")

SELF_PING_INTERVAL = 600  # seconds (10 minutes; Render sleeps after 15)


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


def _self_ping_loop(url: str):
    """GET the service's own public URL every 10 minutes (daemon thread).

    The request goes out to Render's router and back in, which counts as
    HTTP traffic and keeps the free service awake. Failures are ignored
    (logged at debug) so a bad ping never affects the bot.
    """
    while True:
        time.sleep(SELF_PING_INTERVAL)
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                resp.read()
            LOGGER.debug("[INFO]: Self-ping OK (%s)", url)
        except Exception as exc:  # noqa: BLE001 - keep-alive must not crash
            LOGGER.debug("[INFO]: Self-ping failed (%s): %s", url, exc)


def start_health_server():
    """Start the health server in a daemon thread. No-op if PORT unset."""
    port = int(os.environ.get("PORT", "10000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    LOGGER.info("[INFO]: Health server listening on 0.0.0.0:%s", port)
    # Self-ping: keep the free service awake from inside the bot.
    url = os.environ.get("RENDER_EXTERNAL_URL") or "https://kaitokid-bot.onrender.com"
    ping_thread = threading.Thread(target=_self_ping_loop, args=(url,), daemon=True)
    ping_thread.start()
    LOGGER.info("[INFO]: Self-ping enabled, every %ss -> %s", SELF_PING_INTERVAL, url)
    return server
