"""Opt-in acceptance transport: append local quota before each real request.

No retries and no stored response bodies. A missing result is consumed/unknown.
This wraps the product's public pinned transport without changing its policy.
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
from app.infrastructure.resources.github_transport import PinnedPublicTransport


def append_json(path, payload):
    with path.open('x', encoding='utf-8') as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write('\n')
        file.flush()
        os.fsync(file.fileno())


class LedgerStream(httpx.SyncByteStream):
    def __init__(self, stream, finish):
        self.stream, self.finish = stream, finish
        self.complete, self.closed, self.size = False, False, 0
        self.digest = hashlib.sha256()

    def __iter__(self):
        for chunk in self.stream:
            self.size += len(chunk)
            self.digest.update(chunk)
            yield chunk
        self.complete = True

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            self.stream.close()
        finally:
            self.finish(self.complete, self.size, self.digest.hexdigest())


class AcceptanceGitHubTransport(httpx.BaseTransport):
    def __init__(self, root: Path, acceptance_id: str):
        self.root, self.acceptance_id = root, acceptance_id
        self.search_dir = root / '.git/v2-search-quota-20261001'
        self.read_dir = root / '.git/n1-github-read-quota-20261002'
        self.calls = []
        # A consumed AcceptanceId can never be used for another dispatch.
        for directory in (self.search_dir, self.read_dir):
            if not directory.is_dir():
                raise RuntimeError('Existing quota directory is required')
            for path in directory.glob('*request-*.json'):
                if json.loads(path.read_text(encoding='utf-8')).get('acceptance_id') == acceptance_id:
                    raise RuntimeError('AcceptanceId already consumed; no replay')

    def handle_request(self, request):
        if request.method != 'GET' or request.url.host != 'api.github.com' or 'authorization' in request.headers:
            raise RuntimeError('Only anonymous public GET is authorized')
        kind = request.extensions.get('n1_kind')
        if kind == 'search':
            directory, prefix, cap = self.search_dir, '', 6  # historical 3 + new batch 3 (old unknown counts)
        elif kind == 'content':
            directory, prefix, cap = self.read_dir, 'content-', 9
        elif kind == 'metadata':
            directory, prefix, cap = self.read_dir, 'metadata-', 6
        else:
            raise RuntimeError('Explicit request kind is required')
        number = len(list(directory.glob(prefix + 'request-*.json'))) + 1
        if number > cap:
            raise RuntimeError('Existing batch quota exhausted; no dispatch')
        request_path = directory / f'{prefix}request-{number:04d}.json'
        result_path = directory / f'{prefix}result-{number:04d}.json'
        common = dict(acceptance_id=self.acceptance_id, kind=kind, number=number)
        append_json(request_path, dict(**common, method='GET', url=str(request.url),
                    at=datetime.now(timezone.utc).isoformat(), new_batch_cap=3 if kind == 'search' else cap,
                    scope='owned acceptance, explicit public tutorial query, no private data or models'))
        self.calls.append(dict(common, path=request.url.path))
        transport = PinnedPublicTransport()
        try:
            response = transport.handle_request(request)
        except Exception as exc:
            append_json(result_path, dict(**common, unknown=True, error=type(exc).__name__,
                                         note='No automatic replay'))
            transport.close()
            raise

        def finish(complete, size, digest):
            try:
                append_json(result_path, dict(**common, http_status=response.status_code,
                    unknown=not complete, bytes=size, response_sha256=digest,
                    status='succeeded' if complete and response.status_code == 200 else 'failed_or_unknown',
                    note='Transport receipt; semantic inspection stored separately in owned PG/evidence'))
            finally:
                transport.close()
        response.stream = LedgerStream(response.stream, finish)
        return response
