"""Explicit content fixture assembly; contains no goal or runtime routing."""
from copy import deepcopy
from app.infrastructure.domain_pack import load_pack


def reviewed_fixture(filename, stage_keys=None):
    pack = load_pack(filename)
    if stage_keys is None:
        return pack
    selected = set(stage_keys)
    pack['stage_blueprints'] = [s for s in pack['stage_blueprints'] if s['stable_key'] in selected]
    assert {s['stable_key'] for s in pack['stage_blueprints']} == selected
    nodes = {k for s in pack['stage_blueprints'] for k in s['node_keys']}
    pack['knowledge_blueprints'] = [n for n in pack['knowledge_blueprints'] if n['stable_key'] in nodes]
    pack['required_node_keys'] = [k for k in pack.get('required_node_keys', []) if k in nodes]
    pack['practice_blueprints'] = [p for p in pack['practice_blueprints'] if p['section_key'] in selected]
    return deepcopy(pack)
