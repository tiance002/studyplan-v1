"""Read complete published Seed snapshots; never read repository files at runtime."""
import psycopg
from app.core.errors import DependencyUnavailableError
from app.domain.domain_packs.validation import seed_digest, validate_seed
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from app.infrastructure.domain_pack import pack_key_for_goal, unsupported_domain_pack


class DomainPackUnavailableError(DependencyUnavailableError):
    pass


class PgDomainPackCatalog:
    def __init__(self, dsn: str):
        self.dsn = to_psycopg_dsn(dsn)

    def select(self, goal: str) -> dict:
        key = pack_key_for_goal(goal)
        if key is None:
            return unsupported_domain_pack()
        with psycopg.connect(self.dsn) as conn:
            row = conn.execute("SELECT published_payload, content_digest, version FROM public.domain_packs WHERE pack_key=%s AND status='published' ORDER BY version DESC LIMIT 1", (key,)).fetchone()
        if not row or row[0] is None:
            raise DomainPackUnavailableError('受支持方向的已发布 Seed 不可用，请先受控导入', pack_key=key)
        try:
            payload = validate_seed(row[0])
            if seed_digest(payload) != row[1] or payload['pack_key'] != key or payload['version'] != row[2]:
                raise ValueError('Seed digest mismatch')
        except ValueError as exc:
            raise DomainPackUnavailableError('已发布 Seed 校验失败', pack_key=key) from exc
        return payload
