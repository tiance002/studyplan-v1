"""Pure controlled-publication checks. Import validation does not review web content."""
from copy import deepcopy
from datetime import datetime
from ipaddress import ip_address
from urllib.parse import urlsplit

from app.core.ids import require_stable_key
from app.domain.domain_packs.models import DomainPack
from app.domain.enums import DomainPackStatus, StageResourceRole
from app.domain.resources.curation import validate_section_selection


def seed_digest(data):
    import hashlib
    import json
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _url(value):
    parsed = urlsplit(value)
    host = parsed.hostname or ''
    if parsed.scheme not in {'https', 'http'} or not host or parsed.username or parsed.password:
        raise ValueError('Resource URL must be an absolute public HTTP(S) URL without credentials')
    if host.lower() in {'localhost', 'localhost.localdomain'} or '.' not in host or host.lower().endswith(('.local', '.internal', '.localhost')):
        raise ValueError('Resource URL must not reference local hosts')
    try:
        address = ip_address(host)
    except ValueError:
        return
    if not address.is_global:
        raise ValueError('Resource URL must not reference non-public IPs')


def _keys(items, key):
    result = {}
    for item in items:
        value = item[key]
        if not isinstance(value, str) or not value.strip() or value in result:
            raise ValueError(f'Invalid or duplicate {key}')
        if key == 'stable_key':
            require_stable_key(value)
        result[value] = item
    return result


def _refs(values, valid):
    if not isinstance(values, list) or len(set(values)) != len(values) or any(v not in valid for v in values):
        raise ValueError('Missing or duplicate Seed reference')


def _texts(item, fields, empty=()):
    for field in fields:
        value = item[field]
        if not isinstance(value, str) or (field not in empty and not value.strip()):
            raise ValueError(f'Invalid Seed text field: {field}')


def _review(item, section=False):
    status = item.get('verification_status', 'legacy_index')
    if status not in {'reviewed', 'legacy_index', 'unverified'}:
        raise ValueError('Invalid verification status')
    if item.get('checked_at'):
        date = datetime.fromisoformat(item['checked_at'].replace('Z', '+00:00'))
        if date.tzinfo is None:
            raise ValueError('Review date needs a timezone')
    if status == 'reviewed' and (not item.get('checked_at') or (section and not item.get('review_note'))):
        raise ValueError('Reviewed content requires dated provenance')


def validate_seed(raw):
    """Return an isolated JSON payload; reject invalid Seed before any DB write."""
    try:
        data = deepcopy(raw)
        data.setdefault('resource_support', 'reviewed_index')
        pack = DomainPack.create(**{k: data[k] for k in ('pack_key', 'version', 'title', 'supported_scope', 'provenance')},
                                 status=DomainPackStatus(data['status']))
        pack.require_published()
        if type(data['version']) is not int or not data['provenance'].strip():
            raise ValueError('Seed needs a positive integer version and provenance')
        nodes = _keys(data.get('knowledge_blueprints', []), 'stable_key')
        stages = _keys(data['stage_blueprints'], 'stable_key')
        _keys(data['practice_blueprints'], 'stable_key')
        if not stages:
            raise ValueError('Seed needs stage blueprints')
        _refs(data.get('required_node_keys', []), nodes)
        edges = {}
        for key, node in nodes.items():
            _texts(node, ('title', 'node_type'))
            dependencies = node.get('prerequisite_keys', [])
            _refs(dependencies, nodes)
            if node.get('parent_key'):
                _refs([node['parent_key']], nodes)
            edges[key] = dependencies + ([node['parent_key']] if node.get('parent_key') else [])
        visiting, done = set(), set()

        def visit(key):
            if key in visiting:
                raise ValueError('Knowledge dependency cycle')
            if key in done:
                return
            visiting.add(key)
            for dep in edges[key]:
                visit(dep)
            visiting.remove(key)
            done.add(key)
        for key in nodes:
            visit(key)
        sources = _keys(data['resources'], 'source_id')
        _refs(data['resource_refs'], sources)
        all_sections = set()
        for source in sources.values():
            _texts(source, ('canonical_url', 'title', 'creator', 'media_type', 'language'), empty=('creator',))
            if type(source['source_version']) is not int or source['source_version'] < 1:
                raise ValueError('Source version must be a positive integer')
            _url(source['canonical_url'])
            _review(source)
            sections = _keys(source['sections'], 'section_id')
            orders = [s['order_index'] for s in sections.values()]
            if any(type(i) is not int or i < 0 for i in orders) or orders != sorted(set(orders)):
                raise ValueError('Sections need unique increasing nonnegative ordering')
            for key, section in sections.items():
                _texts(section, ('title', 'url'))
                if key in all_sections:
                    raise ValueError('Section IDs must be unique across sources')
                all_sections.add(key)
                _url(section['url'])
                _review(section, section=True)
                _refs(section.get('applicable_node_keys', []), nodes)
        for blueprint in [*stages.values(), *data['practice_blueprints']]:
            _texts(blueprint, ('title',))
            _refs(blueprint.get('node_keys', []), nodes)
        for practice in data['practice_blueprints']:
            _texts(practice, ('goal',))
            if practice.get('section_key'):
                _refs([practice['section_key']], stages)
        for stage in stages.values():
            _texts(stage, ('section_kind', 'objective'))
            roles = stage.get('resources', [])
            if sum(r['role'] == 'primary' for r in roles) > 1:
                raise ValueError('Stage must have at most one primary source')
            for assignment in roles:
                if assignment['role'] not in {role.value for role in StageResourceRole}:
                    raise ValueError('Invalid resource role')
                source = sources[assignment['source_ref']]
                if assignment['source_ref'] not in data['resource_refs'] or assignment['source_version'] != source['source_version']:
                    raise ValueError('Invalid source reference/version')
                sections = _keys(source['sections'], 'section_id')
                _refs(assignment['section_refs'], sections)
                selection_errors = validate_section_selection(
                    source_ref=assignment['source_ref'], section_refs=tuple(assignment['section_refs']),
                    role=StageResourceRole(assignment['role']),
                    catalog_order={key: (assignment['source_ref'], section['order_index'])
                                   for key, section in sections.items()},
                )
                if selection_errors:
                    raise ValueError('; '.join(selection_errors))
                _refs(assignment.get('node_keys', []), stage.get('node_keys', []))
        seed_digest(data)
        return data
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('Malformed Seed payload') from exc
