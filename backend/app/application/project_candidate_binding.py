"""Read-only repository identity from an exact frozen Plan assignment.

This does not review sources, resolve the current catalog or create sections.
"""
import re
from urllib.parse import urlsplit


def frozen_candidate_url(assignment, snapshot):
    source = snapshot.get("source") or {}
    view = snapshot.get("view") or {}
    identity = (assignment.assignment_id, assignment.stage_id, str(assignment.role),
                assignment.source_ref, assignment.source_version)
    fields = ("assignment_id", "stage_id", "role", "source_ref", "source_version")
    if (not assignment.source_ref or assignment.source_version < 1
            or str(assignment.role) != "case_study"
            or tuple(snapshot.get(key) for key in fields) != identity
            or tuple(view.get(key) for key in fields) != identity
            or snapshot.get("snapshot_status") != "frozen"
            or view.get("warnings")
            or source.get("source_id") != assignment.source_ref
            or source.get("source_version") != assignment.source_version
            or source.get("media_type") != "repo" or view.get("media_type") != "repo"
            or source.get("verification_status") not in {"reviewed", "legacy_index"}
            or view.get("verification_status") != source.get("verification_status")
            or not source.get("checked_at")):
        return None
    value = source.get("canonical_url")
    if not isinstance(value, str):
        return None
    try:
        url = urlsplit(value)
        parts = url.path.strip("/").split("/")
        if (url.scheme != "https" or url.hostname not in {"github.com", "gitlab.com", "codeberg.org"}
                or url.port or url.username or url.password or url.query or url.fragment
                or len(parts) != 2 or any(part in {".", ".."} for part in parts)
                or not all(re.fullmatch(r"[\w.-]+", part) for part in parts)):
            return None
    except ValueError:
        return None
    return value
