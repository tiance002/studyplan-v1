"""Explicit file publication using the configured migrator; no project/checkpoint setup."""
import argparse
import json
import os
from pathlib import Path

import psycopg
from app.domain.domain_packs.validation import seed_digest, validate_seed
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from app.tools.seed_b3 import seed_reviewed_pack


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', required=True, type=Path)
    args = parser.parse_args(argv)
    data = validate_seed(json.loads(args.file.read_text(encoding='utf-8-sig')))
    with psycopg.connect(to_psycopg_dsn(os.environ['STUDYPLAN_MIGRATION_DSN'])) as conn:
        seed_reviewed_pack(conn, data)
    print(f"Published {data['pack_key']} v{data['version']} digest={seed_digest(data)}; existing provenance retained")


if __name__ == '__main__':
    main()
