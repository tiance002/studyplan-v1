"""Explicitly opted-in public GitHub + real owned PG + ordinary browser account.

Plan fixture generation is Fake; GitHub responses are real and never replayed.
"""
import os
import socket
import subprocess
import threading
import time
from pathlib import Path

import psycopg
import pytest
import uvicorn
from app.infrastructure.resources.github import GitHubResourceIndex
from app.main import create_app

from tests.helpers.live_github_ledger import AcceptanceGitHubTransport
from tests.integration.test_generated_plan_changes_pg import generated_route as generated_route
from tests.integration.test_generated_plan_changes_pg import migrated_db as migrated_db

pytestmark = pytest.mark.postgres


def test_public_github_search_readme_chapter_private_selection_refresh_relogin(generated_route):
    if os.environ.get('STUDYPLAN_GITHUB_LIVE_ACCEPTANCE') != '1':
        pytest.skip('Explicit public GitHub acceptance opt-in required')
    acceptance_id = os.environ.get('STUDYPLAN_GITHUB_ACCEPTANCE_ID', '')
    assert acceptance_id.startswith('n1-github-20261003-')
    db, container, client, params, _, old = generated_route
    root = Path(__file__).resolve().parents[3]
    transport = AcceptanceGitHubTransport(root, acceptance_id)
    container.resource_service.github = GitHubResourceIndex(transport=transport)
    container.resource_service.request_limit = 1
    container.resource_service.content_limit = 3
    container.resource_service.metadata_limit = 0
    username = client.get('/api/v1/session').json()['username']
    fake_calls = len(container.plan_service._llm.calls)
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    server = uvicorn.Server(uvicorn.Config(create_app(container), log_level='error'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert server.started
        env = dict(os.environ, STUDYPLAN_GITHUB_OWNED_API=f'http://127.0.0.1:{sock.getsockname()[1]}',
                   STUDYPLAN_GITHUB_OWNED_USER=username)
        result = subprocess.run(['node', 'frontend/tests/github-live-pg.browser.cjs'], cwd=root,
                    env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
        assert result.returncode == 0, result.stdout + result.stderr
        assert sum(call['kind'] == 'search' for call in transport.calls) == 1
        assert 2 <= sum(call['kind'] == 'content' for call in transport.calls) <= 3
        assert not any(call['kind'] == 'metadata' for call in transport.calls)
        assert len(container.plan_service._llm.calls) == fake_calls
        with psycopg.connect(db.migrator_dsn) as conn:
            row = conn.execute('SELECT resource_snapshot FROM learning_resource_selections WHERE project_id=%s AND plan_id=%s',
                               (params['project_id'], old['plan_id'])).fetchone()
            assert row is not None
            discovery = row[0]['discovery']
            assert discovery['selection_mapping']['chapter_paths']
            assert all(len(file['content_hash']) == 64 and file['blob_sha'] for file in discovery['files'])
    finally:
        server.should_exit = True
        thread.join(10)
        sock.close()
