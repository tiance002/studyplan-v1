from copy import deepcopy

import pytest
from app.domain.domain_packs.validation import validate_seed
from app.infrastructure.domain_pack import load_pack


def test_current_reviewed_pack_is_valid_without_changing_content():
    pack = load_pack('agent-application-v3.json')
    assert validate_seed(pack) == pack


def test_v3_adds_missing_context_chapter_and_preserves_v2():
    previous = load_pack('agent-application-v2.json')
    current = load_pack('agent-application-v3.json')
    old_stage = next(s for s in previous['stage_blueprints'] if s['stable_key'] == 'stage.context')
    new_stage = next(s for s in current['stage_blueprints'] if s['stable_key'] == 'stage.context')
    assert old_stage['resources'][0]['section_refs'] == ['sec_agent_persistence_v1', 'sec_agent_memory_v1']
    assert new_stage['resources'][0]['section_refs'] == [
        'sec_agent_persistence_v1', 'sec_agent_retrieval_v1', 'sec_agent_memory_v1']
    assert current['resources'] == previous['resources']
    assert current['publication_lineage']['base_version'] == 2
    with pytest.raises(ValueError, match='source order'):
        validate_seed(previous)


@pytest.mark.parametrize('defect', ['cycle', 'reference', 'unsafe_url', 'order', 'version', 'role', 'mapping'])
def test_invalid_seed_is_rejected(defect):
    pack = deepcopy(load_pack('agent-application-v3.json'))
    stage = pack['stage_blueprints'][0]
    if defect == 'cycle':
        pack['knowledge_blueprints'][0]['prerequisite_keys'] = ['node.model_api']
    elif defect == 'reference':
        stage['resources'][0]['section_refs'] = ['missing']
    elif defect == 'unsafe_url':
        pack['resources'][0]['canonical_url'] = 'http://127.0.0.1/private'
    elif defect == 'order':
        stage['resources'][0]['section_refs'].reverse()
    elif defect == 'version':
        stage['resources'][0]['source_version'] = 99
    elif defect == 'role':
        stage['resources'][0]['role'] = 'invented'
    elif defect == 'mapping':
        stage['resources'][0]['node_keys'] = ['missing']
    with pytest.raises(ValueError):
        validate_seed(pack)


def test_historical_v1_reversed_capstone_is_rejected():
    with pytest.raises(ValueError, match='source order'):
        validate_seed(load_pack('agent-application-v1.json'))


def test_historical_python_pack_remains_valid():
    assert validate_seed(load_pack('python-engineering-v1.json'))['version'] == 1


def test_bootstrap_selects_valid_v3_without_database_side_effects(monkeypatch):
    from contextlib import nullcontext
    from types import SimpleNamespace

    from app.tools import seed_b3

    packs = []

    class BootstrapConnection:
        def execute(self, query, args):
            # Record the historical actor/project path without executing SQL.
            assert query.startswith('INSERT INTO learning_projects')

    monkeypatch.setenv('STUDYPLAN_MIGRATION_DSN', 'postgresql://unused/unused')
    monkeypatch.delenv('CHECKPOINT_SETUP_DSN', raising=False)
    monkeypatch.setattr(seed_b3, 'get_settings', lambda: SimpleNamespace(local_project_id='p', local_actor_id='a'))
    monkeypatch.setattr(seed_b3.psycopg, 'connect', lambda *args: nullcontext(BootstrapConnection()))
    monkeypatch.setattr(seed_b3, 'seed_reviewed_pack', lambda conn, data: packs.append(validate_seed(data)))
    seed_b3.main()
    assert [(pack['pack_key'], pack['version']) for pack in packs] == [
        ('python.engineering', 1), ('agent.application', 3)]
