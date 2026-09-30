"""Same B2-V counterexamples over an actual localhost socket and real PG."""
import socket
import threading
import time

import httpx
import pytest
import uvicorn

from tests.e2e import test_b2v_http_end_to_end as cases
from tests.e2e.test_b2v_http_end_to_end import db as db
from tests.e2e.test_b2v_http_end_to_end import migrated_db as migrated_db

pytestmark = pytest.mark.postgres


@pytest.mark.parametrize("case", [
    "test_regression_historical_replay",
    "test_regression_two_windows_and_old_content",
    "test_regression_concurrent_edit",
    "test_regression_catalog_history_and_keys",
])
def test_real_socket_counterexample(case, db, monkeypatch):
    from app.main import create_app
    servers, clients = [], []
    def client_factory(database, *, llm=None, cookie=cases.SESSION_A1):
        app = create_app(cases._container(database,llm=llm))
        sock = socket.socket()
        sock.bind(("127.0.0.1",0))
        sock.listen(64)
        port = sock.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app,host="127.0.0.1",port=port,log_level="error",access_log=False))
        thread = threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True)
        servers.append((server,thread,sock))
        thread.start()
        # This is an in-process localhost server, never an environment proxy.
        client = httpx.Client(base_url=f"http://127.0.0.1:{port}",timeout=60,trust_env=False)
        client.app = app
        client.planning_worker = app.state.container.planning_worker
        clients.append(client)
        for _ in range(100):
            if server.started:
                break
            if not thread.is_alive():
                raise RuntimeError("Socket server failed to start")
            time.sleep(0.02)
        assert server.started
        client.cookies.set(cases.COOKIE,cookie)
        return client
    monkeypatch.setattr(cases,"_client",client_factory)
    try:
        getattr(cases,case)(db)
    finally:
        for client in clients:
            client.close()
        for server,thread,sock in servers:
            server.should_exit=True
            thread.join(timeout=10)
            sock.close()
            assert not thread.is_alive()
