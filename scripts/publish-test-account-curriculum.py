"""Publish the explicitly requested curriculum revision to the retained test account.

This maintenance command is confined to the named isolated preview database.
It does not create a Run, invoke a provider, alter a public Seed, or weaken RLS.
Prepare makes a fresh backup and exercises the normal publisher with rollback.
Publish requires that preparation and uses its exact content and idempotency key.
"""
# ruff: noqa: E402
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

import psycopg
from app.core.ids import new_id
from app.domain.enums import OutlineSectionKind, StageResourceRole
from app.domain.planning.models import (
    PlanDraft,
    PlanPublicationService,
    PlanStage,
    PlanTaskKnowledgeLink,
    PlanTaskLink,
    PlanUnitLink,
)
from app.domain.resources.curation import StageResourceAssignment
from app.infrastructure.db.plan_repository import PgPlanRepository
from app.infrastructure.db.planning_catalog import PgPlanningCatalog
from app.infrastructure.db.planning_fence import lock_plan_version
from app.infrastructure.db.resource_changes import capture_resource_snapshots
from psycopg import sql
from psycopg.rows import dict_row
from tests.pg_harness import APP_ROLE, APP_ROLE_PASSWORD, MIGRATOR_ROLE, MIGRATOR_ROLE_PASSWORD, role_dsn

DATABASE = 'studyplan_test_v2g1real_2f6ac462'
CONTENT = ROOT / 'docs/curriculum/test-account-agent-plan-2026-10-02.json'
DIRECTORY = ROOT / 'var/frontend-redesign/curriculum-review-20261002-01'
PRESERVE_TABLES = ('plan_stages', 'plan_unit_links', 'plan_task_links', 'plan_task_knowledge_links',
                   'stage_resource_assignments', 'knowledge_extensions', 'knowledge_nodes',
                   'knowledge_relations', 'learning_units', 'unit_node_links', 'practice_projects',
                   'practice_tasks', 'summary_attempts', 'summary_stage_heads', 'summary_position_heads',
                   'prompt_revisions', 'practice_submissions', 'acceptance_reviews', 'learning_exposures',
                   'learning_resource_selections', 'ai_runs', 'ai_jobs', 'plan_publications')


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding='utf-8')


def validate_content(data):
    stages = data['stages']
    assert len(stages) == 13
    keys = [s['key'] for s in stages]
    assert len(set(keys)) == len(keys)
    assert keys.index('eval') < keys.index('rlBasics') < keys.index('advancedEval') < keys.index('capstone') < keys.index('rlTraining')
    assert stages[-1]['optional']
    seen = set()
    for stage in stages:
        assert set(stage['prerequisites']) <= seen, 'Prerequisites must precede the stage'
        seen.add(stage['key'])
        assert stage['objective'] and stage['units'] and stage['nodes'] and stage['tasks']
        assert sum(s['role'] == 'primary' for s in stage['sources']) == 1
        node_keys = {n['key'] for n in stage['nodes']}
        assert len(node_keys) == len(stage['nodes'])
        for unit in stage['units']:
            assert unit['objectives'] and unit['rubric'] and set(unit['node_keys']) <= node_keys
        assert set().union(*(set(u['node_keys']) for u in stage['units'])) == node_keys
        for task in stage['tasks']:
            assert len(task['acceptance']) >= 2 and task['goal'] and set(task['node_keys']) <= node_keys
        for source in stage['sources']:
            assert source['url'].startswith('https://') and source['reading'] and source['why']
    for entity in ('nodes', 'units', 'tasks'):
        all_keys = [item['key'] for s in stages for item in s[entity]]
        assert len(set(all_keys)) == len(all_keys)


def scope(conn, ctx):
    conn.execute("SELECT set_config('app.actor_id',%s,true),set_config('app.project_id',%s,true)", (ctx['actor_id'], ctx['project_id']))
    assert conn.execute('SELECT 1 FROM learning_projects WHERE project_id=%s AND owner_actor_id=%s AND archived_at IS NULL', (ctx['project_id'], ctx['actor_id'])).fetchone()


def history(conn, project_id):
    tables = {r['table_name'] for r in conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'").fetchall()}
    result = {}
    for table in PRESERVE_TABLES:
        if table in tables:
            predicate = sql.SQL('run_id IN (SELECT run_id FROM ai_runs WHERE project_id=%s)') if table == 'ai_jobs' else sql.SQL('project_id=%s')
            rows = conn.execute(sql.SQL('SELECT row_to_json(t)::text AS value FROM public.{} t WHERE {}').format(sql.Identifier(table), predicate), (project_id,)).fetchall()
            result[table] = sorted(hashlib.sha256(r['value'].encode()).hexdigest() for r in rows)
    revisions = conn.execute('SELECT plan_id,revision,goal_snapshot,structure,source_pack_key,source_pack_version FROM plan_revisions WHERE project_id=%s ORDER BY revision', (project_id,)).fetchall()
    result['revision_structures'] = [digest(r) for r in revisions]
    return result


def assert_preserved(before, after):
    for table, values in before.items():
        assert set(values) <= set(after[table]), f'Original {table} records changed'


def backup(migration_dsn):
    path = DIRECTORY / 'before-plan-v4.dump'
    if path.exists():
        assert path.stat().st_size > 0
        return
    parsed = urlsplit(migration_dsn)
    assert parsed.hostname == '127.0.0.1' and parsed.path == '/' + DATABASE
    env = dict(os.environ, PGPASSWORD=unquote(parsed.password or ''))
    # Reuse client tools in the already running container; no RAG database change.
    with path.open('xb') as output:
        result = subprocess.run(['docker', 'exec', '-e', 'PGPASSWORD', 'raglocalfirst0930-db-1', 'pg_dump',
                                 '--format=custom', '--no-owner', '--no-acl', '--host', 'host.docker.internal',
                                 '--port', str(parsed.port or 5432), '--username', parsed.username, '--dbname', DATABASE],
                                stdout=output, stderr=subprocess.PIPE, env=env)
    assert result.returncode == 0 and path.stat().st_size > 0, 'Backup failed; do not publish'
    with path.open('rb') as stream:
        checked = subprocess.run(['docker', 'exec', '-i', 'raglocalfirst0930-db-1', 'pg_restore', '--list'],
                                 stdin=stream, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert checked.returncode == 0, 'Backup archive check failed'


def register_catalog(migration_dsn, data, checked_urls):
    """Add versioned page indexes only inside this test database; never UPDATE."""
    with psycopg.connect(migration_dsn, row_factory=dict_row) as conn:
        assert conn.execute('SELECT current_database() AS name').fetchone()['name'] == DATABASE
        for stage in data['stages']:
            for source in stage['sources']:
                assert source['url'] in checked_urls, 'Source has not been reviewed'
                key = hashlib.sha256((source['url'] + '\n' + source['reading']).encode()).hexdigest()[:24]
                source_id, section_id = 'src_review_' + key, 'sec_review_' + key
                conn.execute('''INSERT INTO public_resource_sources(source_id,canonical_url,title,creator,media_type,language,source_version,provenance,checked_at,documentation_version,verification_status)
                    VALUES(%s,%s,%s,%s,'documentation','en',1,%s,now(),%s,'reviewed') ON CONFLICT(source_id) DO NOTHING''',
                    (source_id, source['url'], source['title'], urlsplit(source['url']).hostname,
                     'Explicit test-account curriculum review 2026-10-02; content and page headings inspected, no execution verification', 'Living documentation; review 2026-10-02'))
                conn.execute('''INSERT INTO public_resource_sections(section_id,source_id,order_index,title,url,anchor,checked_at,verification_status,review_note)
                    VALUES(%s,%s,0,%s,%s,'',now(),'reviewed',%s) ON CONFLICT(section_id) DO NOTHING''',
                    (section_id, source_id, source['reading'], source['url'], source['why']))
                row = conn.execute('SELECT canonical_url,title FROM public_resource_sources WHERE source_id=%s', (source_id,)).fetchone()
                assert row['canonical_url'] == source['url'] and row['title'] == source['title']


class TransactionCatalog(PgPlanningCatalog):
    def __init__(self, dsn, conn):
        super().__init__(dsn)
        self.connection = conn

    @contextmanager
    def _tx(self, project_id):
        self.connection.execute("SELECT set_config('app.project_id',%s,true)", (project_id,))
        yield self.connection


def publish(conn, app_dsn, ctx, data, intent):
    scope(conn, ctx)
    lock_plan_version(conn, ctx['project_id'], 3)
    assert conn.execute("SELECT count(*) AS n FROM ai_runs WHERE project_id=%s AND status IN ('queued','running','reconciliation_required')", (ctx['project_id'],)).fetchone()['n'] == 0
    before = history(conn, ctx['project_id'])
    repo = PgPlanRepository(app_dsn, connection=conn)
    current = repo.get_current(project_id=ctx['project_id'])
    assert current.revision == 3
    nodes, units, tasks, relations = [], [], [], []
    first = {s['key']: s['nodes'][0]['key'] for s in data['stages']}
    for stage in data['stages']:
        nodes.extend(dict(stable_key=n['key'], title=n['title'], objectives=n['objectives'], node_type='concept') for n in stage['nodes'])
        units.extend(dict(stable_key=u['key'],title=u['title'],objectives=u['objectives'],rubric=u['rubric'],node_keys=u['node_keys']) for u in stage['units'])
        tasks.extend(dict(stable_key=t['key'],title=t['title'],goal=t['goal'],in_scope=t['in_scope'],out_scope=t['out_scope'],acceptance=t['acceptance'],knowledge_links=[dict(node_stable_key=k,role='core') for k in t['node_keys']]) for t in stage['tasks'])
        for node in stage['nodes'][1:]:
            relations.append(dict(from_stable_key=first[stage['key']],to_stable_key=node['key'],relation_type='prerequisite'))
        for prerequisite in stage['prerequisites']:
            previous = next(s for s in data['stages'] if s['key'] == prerequisite)
            for prerequisite_node in previous['nodes']:
                relations.append(dict(from_stable_key=prerequisite_node['key'],to_stable_key=first[stage['key']],relation_type='prerequisite'))
    ids = TransactionCatalog(app_dsn, conn).materialize(project_id=ctx['project_id'],nodes=nodes,units=units,relations=relations,
        practice=dict(stable_key='review.knowledge-agent',title='可复现、可评估的知识库 Agent',idea='逐阶段构建只读知识助手，保留来源、工具轨迹和回归评测，不要求使用全部可选框架。',tasks=tasks),expected_plan_version=3)
    stages, unit_links, task_links, knowledge_links, resources = [], [], [], [], []
    for index, stage in enumerate(data['stages']):
        title = stage['title']
        if stage.get('optional') and '可选' not in title:
            title = '可选：' + title
        objective = stage['objective']
        if stage['prerequisites']:
            objective += ' 先修：' + '、'.join(s['title'] for s in data['stages'] if s['key'] in stage['prerequisites']) + '。'
        s = PlanStage.create(stable_key='review.' + stage['key'], title=title,
                             section_kind=OutlineSectionKind.ADVANCED if stage.get('optional') else OutlineSectionKind.CORE,
                             order_index=index,objective=objective)
        stages.append(s)
        unit_links.extend(PlanUnitLink(s.stage_id,ids.unit_ids[u['key']],i) for i,u in enumerate(stage['units']))
        task_links.extend(PlanTaskLink(s.stage_id,ids.task_ids[t['key']],i) for i,t in enumerate(stage['tasks']))
        knowledge_links.extend(PlanTaskKnowledgeLink(ids.task_ids[t['key']],ids.node_ids[k]) for t in stage['tasks'] for k in t['node_keys'])
        for i, source in enumerate(stage['sources']):
            key = hashlib.sha256((source['url'] + '\n' + source['reading']).encode()).hexdigest()[:24]
            resources.append(StageResourceAssignment.create(project_id=ctx['project_id'],stage_id=s.stage_id,
                role=StageResourceRole('supplement' if source['role'] == 'supplemental' else source['role']),source_ref='src_review_' + key,section_refs=('sec_review_' + key,),
                order_index=i,source_version=1,node_ids=tuple(ids.node_ids[n['key']] for n in stage['nodes'])))
    snapshots = capture_resource_snapshots(conn, resources, stages)
    assert all(not r['view']['warnings'] and r['view']['ordered_sections'] for r in snapshots)
    draft = PlanDraft(intent['draft_id'],ctx['project_id'],'',current.goal_snapshot,4,stages=tuple(stages),unit_links=tuple(unit_links),
        task_links=tuple(task_links),task_knowledge_links=tuple(knowledge_links),stage_resources=tuple(resources),resource_snapshots=snapshots,
        node_stable_keys=tuple(ids.node_ids),unit_refs=tuple(ids.unit_ids),task_refs=tuple(ids.task_ids),
        source_pack_key=current.source_pack_key,source_pack_version=current.source_pack_version,
        practice_project_idea='知识库Agent课程手动修订，依据2026-10-02用户已确认的教学安排。',
        validation_warnings=('测试账号手动课程修订；未发布新的公共Seed。','完整RL训练与MCP为可选进阶；没有阶段通关门槛或每日总结。','旧版本、总结、Prompt及成果原文保留；新位置不继承完成状态。'))
    repo.save_draft(draft,expected_version=3)
    result = PlanPublicationService(repo).publish(draft=draft,presented_hash=draft.content_hash,expected_version=3,idempotency_key=intent['idempotency_key'])
    assert result.revision == 4 and result.created
    after = history(conn, ctx['project_id'])
    assert_preserved(before, after)
    return dict(asdict(result),project_id=ctx['project_id'],draft_id=draft.draft_id,draft_hash=draft.content_hash,
                content_sha=intent['content_sha'],before_history=before,stage_titles=[s.title for s in stages],
                stages=len(stages),units=len(units),nodes=len(nodes),tasks=len(tasks),resources=len(resources),history_preserved=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('prepare','publish','verify'))
    args = parser.parse_args()
    data = json.loads(CONTENT.read_text(encoding='utf-8'))
    validate_content(data)
    ctx = json.loads((ROOT/'var/v2-g1/v2-g1-20261001-01-browser-private.json').read_text(encoding='utf-8'))
    assert ctx['business_database'] == DATABASE
    app_dsn = role_dsn(APP_ROLE, APP_ROLE_PASSWORD, DATABASE)
    migration_dsn = role_dsn(MIGRATOR_ROLE, MIGRATOR_ROLE_PASSWORD, DATABASE)
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    intent_path, result_path = DIRECTORY/'intent.json', DIRECTORY/'result.json'
    sha = hashlib.sha256(CONTENT.read_bytes()).hexdigest()
    if args.mode == 'prepare':
        assert not result_path.exists(), 'Already completed; use verify'
        checked = json.loads((DIRECTORY/'reviewed-urls.json').read_text(encoding='utf-8'))
        backup(migration_dsn)
        register_catalog(migration_dsn, data, checked)
        if intent_path.exists():
            intent = json.loads(intent_path.read_text(encoding='utf-8'))
            assert intent['content_sha'] == sha
        else:
            intent = dict(content_sha=sha,draft_id=new_id('drf'),idempotency_key=new_id('cur'))
            write_json(intent_path,intent)
        with psycopg.connect(app_dsn,row_factory=dict_row) as conn:
            result = publish(conn,app_dsn,ctx,data,intent)
            conn.rollback()
        write_json(DIRECTORY/'dry-run.json', result)
        print(json.dumps({'status':'PASS','mode':'prepare','rolled_back':True,'stages':result['stages'],'tasks':result['tasks']}))
    elif args.mode == 'publish':
        assert not result_path.exists(), 'Already completed; use verify'
        intent = json.loads(intent_path.read_text(encoding='utf-8'))
        prepared = json.loads((DIRECTORY/'dry-run.json').read_text(encoding='utf-8'))
        assert intent['content_sha'] == sha == prepared['content_sha']
        # Recover an unknown local outcome via the original receipt, never a new intent.
        with psycopg.connect(app_dsn,row_factory=dict_row) as conn:
            scope(conn,ctx)
            repo = PgPlanRepository(app_dsn,connection=conn)
            receipt = repo.find_publish_by_idempotency_key(project_id=ctx['project_id'],idempotency_key=intent['idempotency_key'])
            if receipt:
                assert receipt.revision == 4 and repo.get_current(project_id=ctx['project_id']).plan_id == receipt.plan_id
                result = dict(prepared,plan_id=receipt.plan_id,structure_fingerprint=receipt.structure_fingerprint,recovered=True)
                assert_preserved(prepared['before_history'],history(conn,ctx['project_id']))
            else:
                result = publish(conn,app_dsn,ctx,data,intent)
        write_json(result_path,result)
        print(json.dumps({'status':'PASS','mode':'publish','revision':result['revision'],'stages':result['stages'],'history_preserved':True}))
    else:
        result = json.loads(result_path.read_text(encoding='utf-8'))
        assert result['content_sha'] == sha
        with psycopg.connect(app_dsn,row_factory=dict_row) as conn:
            conn.execute('SET TRANSACTION READ ONLY')
            scope(conn,ctx)
            current = PgPlanRepository(app_dsn,connection=conn).get_current(project_id=ctx['project_id'])
            assert current.plan_id == result['plan_id'] and current.revision == 4 and len(current.stages) == 13
            assert_preserved(result['before_history'],history(conn,ctx['project_id']))
        print(json.dumps({'status':'PASS','mode':'verify','revision':4,'history_preserved':True}))


if __name__ == '__main__':
    main()
