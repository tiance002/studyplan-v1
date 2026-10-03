from copy import deepcopy

import pytest
from app.domain.domain_packs.validation import validate_seed
from app.infrastructure.domain_pack import load_pack


def semantic_pack():
    data = deepcopy(load_pack('ai-fullstack-v1.json'))
    data['semantic_policy'] = {'version': 1}
    for source in data['resources']:
        source.update(review_depth='selected_sections_read', content_access='free_public', public_seed_status='mapping_ready_review_pending')
        source['review_evidence'] = {'review_depth': 'selected_sections_read'}
    return data


@pytest.mark.parametrize('status', ['hold_identity_review', 'hold_content_review', 'hold_access_review'])
def test_hold_is_rejected_before_any_database_write(status):
    data = semantic_pack()
    data['resources'][0]['public_seed_status'] = status
    with pytest.raises(ValueError, match='hold'):
        validate_seed(data)


@pytest.mark.parametrize('field,value', [('review_depth', 'metadata_only'), ('review_depth', 'toc_checked'), ('content_access', 'unknown')])
def test_primary_cannot_gain_unsupported_review_or_access(field, value):
    data = semantic_pack()
    ref = data['stage_blueprints'][0]['resources'][0]['source_ref']
    source = next(s for s in data['resources'] if s['source_id'] == ref)
    source[field] = value
    with pytest.raises(ValueError, match='Primary|depth'):
        validate_seed(data)


def test_reviewed_section_cannot_inflate_directory_only_evidence():
    data = semantic_pack()
    section = data['resources'][0]['sections'][0]
    section.update(review_depth='toc_checked', verification_status='reviewed', review_note='目录而已')
    with pytest.raises(ValueError, match='depth'):
        validate_seed(data)


def test_legacy_publication_contract_is_unchanged():
    original = load_pack('agent-application-v4.json')
    assert validate_seed(original) == original


def test_section_cannot_claim_more_reading_than_its_source():
    data = semantic_pack()
    source = data['resources'][0]
    source['review_depth'] = 'metadata_only'
    source['sections'][0].update(review_depth='selected_sections_read', verification_status='reviewed')
    for stage in data['stage_blueprints']:
        for assignment in stage['resources']:
            if assignment['source_ref'] == source['source_id']:
                assignment['role'] = 'supplement'
    with pytest.raises(ValueError, match='depth'):
        validate_seed(data)


@pytest.mark.parametrize('evidence', [None, {'review_depth': 'toc_checked'}])
def test_body_review_requires_original_evidence_without_upgrading_it(evidence):
    data = semantic_pack()
    if evidence is None:
        data['resources'][0].pop('review_evidence')
    else:
        data['resources'][0]['review_evidence'] = evidence
    with pytest.raises(ValueError, match='original|upgraded'):
        validate_seed(data)


@pytest.mark.parametrize('file', ['ai-fullstack-v2.json', 'agent-application-v5.json', 'cloud-services-v2.json'])
def test_current_semantic_versions_cannot_drop_the_publication_guard(file):
    data = load_pack(file)
    data.pop('semantic_policy')
    with pytest.raises(ValueError, match='policy'):
        validate_seed(data)
