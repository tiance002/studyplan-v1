"""Alignment cases via ordinary auth/worker/Fake/publication in new owned PG."""
import json
import os
import subprocess
import sys
import time
from copy import deepcopy
from pathlib import Path

import psycopg
import pytest
from app.agent_workflows.planning_batches import manifest_is_intact
from app.composition import build_container
from app.domain.domain_packs.validation import seed_digest
from app.infrastructure.domain_pack import CURRENT_PACKS, load_pack
from app.main import create_app
from app.tools.map_semantic_content import bounded_extensions
from app.tools.seed_b3 import seed_reviewed_pack
from fastapi.testclient import TestClient

from tests.integration.test_v62_semantic_pg import confirm, generate, register, settings_for
from tests.pg_harness import create_test_database, roles_created_by_harness

pytestmark = pytest.mark.postgres
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'var/v610'
SCENARIOS = [
    ('system', '零基础系统学习 Agent 应用开发，先做一个最小应用。', 'agent.application'),
    ('mcp', '我只想学 MCP；已经会基础 Tool 调用。', 'agent.application'),
    ('node', '我已有一个 Node.js API，希望学习部署、监控、自动发布和恢复。', 'cloud.services'),
    ('travel', '我已有一个旅行规划 Agent，希望系统补齐 Agent 应用开发能力。', 'agent.application'),
    ('commerce', '我已有一个电商后台，想开发 AI 全栈商品文案与客服。', 'ai.fullstack'),
    ('rag', '系统学 Agent，重点 RAG 和成熟项目学习。', 'agent.application'),
]


@pytest.fixture(scope='module')
def alignment_db():
    OUT.mkdir(parents=True, exist_ok=True)
    db = create_test_database('studyplan_test_v610_fake')
    assert not roles_created_by_harness(), 'No global role changes authorized'
    ready = False
    try:
        migration = subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], cwd=ROOT / 'backend',
            env=dict(os.environ, STUDYPLAN_MIGRATION_DSN=db.migrator_dsn), capture_output=True,
            text=True, encoding='utf-8', errors='replace')
        assert migration.returncode == 0, migration.stderr
        with psycopg.connect(db.migrator_dsn) as connection:
            for filename in ('agent-application-v5.json', 'ai-fullstack-v2.json', 'cloud-services-v2.json'):
                seed_reviewed_pack(connection, load_pack(filename))
            for key in ('agent.application', 'ai.fullstack', 'cloud.services'):
                seed_reviewed_pack(connection, load_pack(CURRENT_PACKS[key]))
                seed_reviewed_pack(connection, load_pack(CURRENT_PACKS[key]))
        if os.environ.get('STUDYPLAN_V610_KEEP_OWNED') == '1':
            private = OUT / 'private'
            private.mkdir(exist_ok=True)
            (private / 'fake-database.json').write_text(json.dumps(db.__dict__), encoding='utf-8')
        ready = True
        yield db
    finally:
        if not ready or os.environ.get('STUDYPLAN_V610_KEEP_OWNED') != '1':
            db.drop()


def frozen(db, run_id):
    with psycopg.connect(db.migrator_dsn) as connection:
        return connection.execute("SELECT detail FROM ai_run_events WHERE run_id=%s AND detail->>'kind'='planning_submission'", (run_id,)).fetchone()[0]




def test_old_pack_is_immutable_in_owned_catalog(alignment_db):
    old = load_pack('agent-application-v5.json')
    changed = deepcopy(old)
    changed['stage_blueprints'][0]['title'] += '不应发布'
    with psycopg.connect(alignment_db.migrator_dsn) as connection:
        with pytest.raises(ValueError):
            seed_reviewed_pack(connection, changed)
        connection.rollback()
        assert connection.execute('SELECT content_digest FROM domain_packs WHERE pack_key=%s AND version=5',
                                  ('agent.application',)).fetchone()[0] == seed_digest(old)


def test_long_project_guidance_fixture_pg_roundtrip():
    # A separate synthetic publication in its own new DB; no change to CURRENT
    # candidate, existing owned publication, or historical published version.
    db = create_test_database('studyplan_test_v610_cards')
    try:
        migration = subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], cwd=ROOT / 'backend',
            env=dict(os.environ, STUDYPLAN_MIGRATION_DSN=db.migrator_dsn), capture_output=True,
            text=True, encoding='utf-8', errors='replace')
        assert migration.returncode == 0, migration.stderr
        fixture = load_pack(CURRENT_PACKS['agent.application'])
        fixture['version'] = 7
        g6 = next(s for s in fixture['stage_blueprints'] if s['stage_code'] == 'G6')
        candidate = next(e for e in g6['extensions'] if e['topic'].startswith('项目学习：') and 'RAGFlow' in e['topic'])
        text = '学习方式：targeted_deep_dive\n' + 'PG 合成验收：检查状态与恢复证据。' * 60 + '\n最终产出与迁移必须完整保留。'
        candidate['guidance'] = text
        g6['extensions'] = bounded_extensions(g6)
        with psycopg.connect(db.migrator_dsn) as connection:
            seed_reviewed_pack(connection, fixture)
        container = build_container(settings_for(db))
        with TestClient(create_app(container)) as client:
            _, params, headers = register(client, 'v610cards')
            run, url, draft = generate(client, container, params, headers, '系统学习 Agent，重点 RAG。')
            plan = confirm(client, params, headers, url, draft)
            stage_id = next(s['stage_id'] for s in plan['stages'] if s['stable_key'] == g6['stable_key'])
            candidates = [e for e in plan['extensions'] if e['stage_id'] == stage_id and e['topic'].startswith('项目学习：')]
            fragments = sorted((e for e in candidates if 'RAGFlow' in e['topic']), key=lambda e: e['order_index'])
            assert len(fragments) >= 2
            assert text in ''.join(e['guidance'] for e in fragments)
            assert any('WeKnora' in e['topic'] for e in candidates)
            assert all(len(e['guidance']) <= 850 for e in candidates)
            assert client.get('/api/v1/workspace', params=params).json()['plan'] == plan
            (OUT / 'long-guidance-pg.json').write_text(json.dumps({'status': 'PASS', 'provider': 'Fake',
                'fixture': 'synthetic version 7 only in separate owned DB, not CURRENT_PACKS', 'run_id': run['run_id'],
                'text_chars': len(text), 'fragments': len(fragments), 'candidate_count': 2,
                'ordered_lossless_readback': 'PASS', 'real_provider_requests': 0}), encoding='utf-8')
    finally:
        db.drop()
