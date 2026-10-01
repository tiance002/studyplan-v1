from dataclasses import replace

import pytest
from app.core.errors import ValidationAppError
from app.domain.practice_changes import KnowledgeChoice, PracticeChangeCommand, TaskChange


def command(**changes):
    values = dict(
        project_id="p",
        plan_id="plan",
        practice_project_id="practice",
        title="A project",
        idea="A clear useful project idea",
        repo_url=None,
        task_changes=(),
        expected_version=1,
        copy_policy="copy_active",
        idempotency_key="key",
    )
    values.update(changes)
    return PracticeChangeCommand(**values)


def task(**changes):
    values = dict(
        operation="update",
        client_key="one",
        task_id="task",
        stage_id="stage",
        title="Task",
        goal="Observable goal",
        in_scope=("feature",),
        out_scope=("no tests invented",),
        acceptance=("show result",),
        knowledge_links=(KnowledgeChoice("node", "core"),),
    )
    values.update(changes)
    return TaskChange(**values)


def test_manual_design_has_closed_core_and_identity_rules():
    assert command(task_changes=(task(),)).input_hash()
    for changes in (
        {"operation": "add"},
        {"task_id": None},
        {"knowledge_links": (KnowledgeChoice("node", "supporting"),)},
        {"knowledge_links": (KnowledgeChoice("node", "core"), KnowledgeChoice("node", "extension"))},
        {"acceptance": ()},
        {"title": "x\x00"},
    ):
        with pytest.raises(ValidationAppError):
            task(**changes)
    with pytest.raises(ValidationAppError):
        command(task_changes=(task(), replace(task(), client_key="two")))


@pytest.mark.parametrize(
    "url",
    [
        "file:///private",
        "javascript:alert(1)",
        "https://user:secret@example.com/repo",
        "https://",
        "https://host/path\nsecret",
    ],
)
def test_repo_metadata_rejects_unsafe_or_secret_uri(url):
    with pytest.raises(ValidationAppError) as error:
        command(repo_url=url)
    assert url not in str(error.value)
