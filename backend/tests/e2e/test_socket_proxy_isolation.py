"""A hostile environment proxy must never intercept the localhost harness."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

from tests.e2e import test_b2v_http_end_to_end as cases
from tests.e2e.test_b2v_http_end_to_end import db as db
from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db
from tests.e2e.test_b2v_socket_counterexamples import test_real_socket_counterexample as run_case

pytestmark = pytest.mark.postgres


def test_localhost_ignores_environment_proxy(db, monkeypatch):
    intercepted = []

    class Proxy(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            intercepted.append("POST")
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            with httpx.Client(trust_env=False) as direct:
                response = direct.post(self.path, content=body, headers={
                    key: value for key, value in self.headers.items()
                    if key.lower() not in {"host", "connection", "content-length"}
                })
            self.send_response(response.status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(response.content)

        def do_GET(self):
            intercepted.append("GET")
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"detail": "Not Found"}).encode())

    proxy = ThreadingHTTPServer(("127.0.0.1", 0), Proxy)
    thread = threading.Thread(target=proxy.serve_forever, daemon=True)
    thread.start()
    address = f"http://127.0.0.1:{proxy.server_port}"
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.setenv(name, address)
    for name in ("NO_PROXY", "no_proxy"):
        monkeypatch.setenv(name, "")

    def scenario(database):
        client = cases._client(database)
        created = cases._generate(client)
        row = client.app.state.container.plan_service._runs.get_run(
            project_id=cases.PROJECT_P1, run_id=created["run_id"],
        )
        assert row is not None and row.status.value == "waiting_user"
        cases._get_run(client, created["run_id"])

    monkeypatch.setattr(cases, "proxy_visibility_scenario", scenario, raising=False)
    try:
        run_case("proxy_visibility_scenario", db, monkeypatch)
        assert intercepted == [], "localhost traffic leaked to an environment proxy"
    finally:
        proxy.shutdown()
        proxy.server_close()
        thread.join(timeout=5)
