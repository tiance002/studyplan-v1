"""Consumer contracts: chapter fidelity, publication qualification and reproducibility."""
import importlib
import json
from pathlib import Path

import pytest
from app.domain.domain_packs.validation import validate_seed

ROOT = Path(__file__).resolve().parents[3]
RESEARCH = ROOT / 'docs/research/semantic-corrected-2026-10-04'
CONTENT = ROOT / 'backend/app/infrastructure/content'


def mapped():
    module = ROOT / 'backend/app/tools/map_semantic_content.py'
    assert module.exists(), 'Offline semantic mapper has not been implemented'
    return importlib.import_module('app.tools.map_semantic_content').build_all(RESEARCH)


def test_detailed_chapters_survive_mapping_and_consumer_validation():
    packs, report = mapped()
    expected = {'agent.application': (5, 61), 'ai.fullstack': (2, 11), 'cloud.services': (2, 15)}
    for pack in packs:
        version, count = expected[pack['pack_key']]
        assert pack['version'] == version
        assert len(pack['stage_blueprints']) == count
        assert validate_seed(pack) == pack
        for stage in pack['stage_blueprints']:
            evidence = stage['teaching_evidence']
            assert all(evidence[k] for k in ('why_now', 'jit_prerequisite', 'primary_chapters',
                       'supplement_comparison', 'exposure_relation', 'small_practice',
                       'outcome_increment', 'exit_gate'))
            assert stage['learning_guidance']['practice_delta']['validation']
    assert report['catalog_records'] == 86


def test_hold_and_partial_reading_cannot_become_reviewed_primary():
    packs, report = mapped()
    assert set(report['holds']) == {'zcode-softorize-identity', 'zcode-zerx-identity',
                                  'maxkb-metadata-reference', 'alibaba-cloudnative-access'}
    for pack in packs:
        sources = {s['source_id']: s for s in pack['resources']}
        assert all(not s['public_seed_status'].startswith('hold_') for s in sources.values())
        for stage in pack['stage_blueprints']:
            for assignment in stage['resources']:
                source = sources[assignment['source_ref']]
                if assignment['role'] == 'primary':
                    assert source['review_depth'] in {'selected_sections_read', 'deep_reviewed'}
                    assert source['content_access'] in {'free_public', 'free_account'}
                sections = {s['section_id']: s for s in source['sections']}
                chosen = [sections[key] for key in assignment['section_refs']]
                assert [s['order_index'] for s in chosen] == sorted(s['order_index'] for s in chosen)
                assert all(s['review_depth'] not in {'metadata_only', 'toc_checked'} or
                           s['verification_status'] != 'reviewed' for s in chosen)


def test_project_cards_are_optional_root_candidates_with_all_nine_fields():
    packs, _ = mapped()
    cards = [e for p in packs for s in p['stage_blueprints'] for e in s['extensions']
             if e.get('project_study_card')]
    assert len(cards) == 12
    fields = {'repo_url', 'why_now', 'learning_focus', 'prerequisites', 'desired_depth',
              'avoid_scope', 'important_questions', 'expected_outputs', 'migration_candidates'}
    for extension in cards:
        card = extension['project_study_card']
        assert fields <= card.keys()
        assert extension['required'] is False
        assert card['binding'] == 'optional' and card['replacement_allowed'] is True
        assert len(card['repo_url'].removeprefix('https://github.com/').split('/')) == 2
        assert not any(key in card for key in ('commit', 'branch', 'files', 'function'))


def test_recipe_selection_is_open_and_training_is_not_application_requirement():
    packs, _ = mapped()
    agent = next(p for p in packs if p['pack_key'] == 'agent.application')
    stages = agent['stage_blueprints']
    for recipe in ('rag', 'coding', 'workflow', 'browser', 'evaluation', 'agentic_rl'):
        matches = [s for s in stages if s.get('recipe') == recipe]
        assert matches and all(not s['selection']['default'] for s in matches)
    training = [s for s in stages if s.get('stage_code') in {'R5', 'R6', 'R7', 'R8', 'R9'}]
    assert len(training) == 5 and all('training' in s['selection']['capabilities'] for s in training)
    assert all(not s['selection']['default'] for s in training)
    cloud = next(p for p in packs if p['pack_key'] == 'cloud.services')
    assert cloud['stage_blueprints'][0]['selection']['skip_when_any']


def test_mapper_is_reproducible_without_changing_research_or_old_packs():
    first, report = mapped()
    second, second_report = mapped()
    assert first == second and report == second_report
    for pack in first:
        path = CONTENT / {'agent.application': 'agent-application-v5.json',
                          'ai.fullstack': 'ai-fullstack-v2.json',
                          'cloud.services': 'cloud-services-v2.json'}[pack['pack_key']]
        assert path.exists(), 'Published JSON artifact missing'
        assert json.loads(path.read_text(encoding='utf-8')) == pack
    all_ids = [s['source_id'] for p in first for s in p['resources']]
    assert len(all_ids) == len(set(all_ids)), 'Pack namespaces must prevent immutable source collisions'


def test_missing_research_evidence_is_an_explicit_error():
    mapped()
    mapper = importlib.import_module('app.tools.map_semantic_content')
    with pytest.raises((ValueError, FileNotFoundError)):
        mapper.build_all(RESEARCH / 'missing-inputs')


def test_nested_authored_reading_and_stage_boundaries_are_preserved():
    packs, _ = mapped()
    ai = next(p for p in packs if p['pack_key'] == 'ai.fullstack')
    f2 = next(s for s in ai['stage_blueprints'] if s['stage_code'] == 'F2')
    assert 'Thinking in React' in f2['teaching_evidence']['primary_chapters']
    cloud = next(p for p in packs if p['pack_key'] == 'cloud.services')
    s13 = cloud['stage_blueprints'][-1]
    assert 'PROJECT_STUDY_CARDS' not in s13['teaching_evidence']['raw_body']


def test_optional_topics_are_not_forced_by_later_recipe_or_existing_service():
    packs, _ = mapped()
    agent = next(p for p in packs if p['pack_key'] == 'agent.application')
    nodes = {n['stable_key']: n for n in agent['knowledge_blueprints']}
    for later, optional in [('c8', 'c7'), ('w7', 'w6'), ('b6', 'b5')]:
        assert 'node.v62.agent.application.' + optional not in nodes['node.v62.agent.application.' + later]['prerequisite_keys']
    cloud = next(p for p in packs if p['pack_key'] == 'cloud.services')
    assert cloud['stage_blueprints'][0]['selection']['fallback_only'] is True
    assert all('node.v62.cloud.services.sm1' not in n['prerequisite_keys'] for n in cloud['knowledge_blueprints'])


def test_primary_continuations_preserve_exact_chosen_scope_without_gap_filling():
    packs, report = mapped()
    splits = [split for record in report['publication_records'] for split in record['primary_continuations']]
    assert splits
    for split in splits:
        assert split['original_section_refs'] == split['primary_section_refs'] + split['supplement_section_refs']
        assert len(split['original_section_refs']) == len(set(split['original_section_refs']))
    agent = next(p for p in packs if p['pack_key'] == 'agent.application')
    g1 = next(s for s in agent['stage_blueprints'] if s['stage_code'] == 'G1')
    sources = {s['source_id']: s for s in agent['resources']}
    selected = []
    for resource in g1['resources']:
        sections = {s['section_id']: s for s in sources[resource['source_ref']]['sections']}
        selected.extend(sections[ref]['title'] for ref in resource['section_refs'])
    assert selected == ['ch2/04 数据加载', 'ch2/05 文本切块', 'ch8/02 数据准备/父子块']


def test_directory_only_and_recommended_only_details_are_candidates():
    packs, report = mapped()
    candidates = [section for p in packs for source in p['resources'] for section in source['sections']
                  if 'Network/Frames/Dialogs' in section['title'] or 'OIDC provider' in section['title']
                  or '10.1 协议角色' in section['title']]
    assert len(candidates) == 3
    assert all(s['review_depth'] == 'toc_checked' and s['verification_status'] == 'legacy_index' for s in candidates)
    for pack in packs:
        for stage in pack['stage_blueprints']:
            for resource in stage['resources']:
                if any(s['section_id'] in resource['section_refs'] for s in candidates):
                    assert resource['role'] != 'primary'
    assert report['section_qualification_limits']
