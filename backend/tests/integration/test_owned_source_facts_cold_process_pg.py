"""Fresh owned databases, two independent native processes, one first-goal pause."""

import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

from backend.tests.integration import test_v2_planning_runtime_pg as fixture

pytestmark = pytest.mark.postgres
ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "var/planning-v2-source-facts-cold-process-20261010"
HELPER = Path(__file__).with_name("owned_source_facts_cold_process.py")


@pytest.fixture(scope="module")
def db():
    old = fixture.EVIDENCE
    fixture.EVIDENCE = EVIDENCE
    generator = fixture.db.__wrapped__()
    try:
        yield next(generator)
    finally:
        fixture.EVIDENCE = old


@pytest.fixture(scope="module")
def checkpoint_db():
    old = fixture.EVIDENCE
    fixture.EVIDENCE = EVIDENCE
    generator = fixture.checkpoint_db.__wrapped__()
    try:
        yield next(generator)
    finally:
        fixture.EVIDENCE = old


def test_real_worker_restores_frozen_sources_after_process_a_ends(db, checkpoint_db):
    folder = EVIDENCE / ("cold-" + uuid4().hex[:12])
    folder.mkdir(parents=True)
    env = dict(
        os.environ,
        PYTHONPATH=os.pathsep.join((str(ROOT), str(ROOT / "backend"))),
        PYTHONIOENCODING="utf-8",
        COLD_TEST_APP_DSN=db.app_dsn,
        COLD_TEST_CHECKPOINT_DSN=checkpoint_db.app_dsn,
        COLD_TEST_MIGRATOR_DSN=db.migrator_dsn,
    )
    for phase, cwd in (("A", ROOT), ("B", ROOT / "backend")):
        result = subprocess.run(
            [sys.executable, str(HELPER), phase, str(folder)],
            cwd=cwd,
            env=env,
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=60,
        )
        (folder / ("process-" + phase.lower() + ".log")).write_text(
            result.stdout + result.stderr, encoding="utf-8"
        )
        assert result.returncode == 0, result.stdout + result.stderr
    first = json.loads((folder / "phase-a.json").read_bytes())
    second = json.loads((folder / "phase-b.json").read_bytes())
    assert first["pid"] != second["pid"] and first["cwd"] != second["cwd"]
    assert first["snapshot"] == second["snapshot"] and first["facts"] == second["facts"]
    assert first["mock_calls"] == first["state"]["provider_attempts"] == 0
    assert second["mock_calls"] == second["state"]["provider_attempts"] == 1
    assert second["state"]["status"] == "waiting_user" and second["review_stage"] == "goal_analysis"
    assert all(
        row["result"] == "PASS" and row["external_invocations"] == 0 for row in second["negative_matrix"]
    )
    assert {row["variant"] for row in second["negative_matrix"]} == {
        "missing",
        "bytes",
        "snapshot_version",
        "unknown_field",
        "facts_hash_corruption",
        "manifest_mismatch",
        "corehash_created_at",
        "corehash_source_version",
    }
    assert all(
        row["provider_resolutions"] == row["mock_calls"] == row["forbidden_port_attempts"] == 0
        for row in second["negative_matrix"]
    )
    assert second["external_invocations"] == second["search_body_calls"] == second["reader_calls"] == 0
    assert second["metadata_transport_configured"] is False
