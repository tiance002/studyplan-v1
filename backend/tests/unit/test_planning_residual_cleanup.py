"""Residual cleanup boundaries, without database or provider dispatch."""
import ast
import importlib
from pathlib import Path

from app.agent_workflows import graphs
from app.api.v1.schemas import GoalSpec
from app.main import create_app


def test_retired_long_graph_is_not_an_application_entry_point():
    for name in ("run_planning_graph", "build_planning_graph", "_await_approval", "_cancel_draft"):
        assert not hasattr(graphs, name)
    from app.agent_workflows.nodes import PlanningNodes
    assert not hasattr(PlanningNodes, "await_approval")
    assert not hasattr(PlanningNodes, "cancel_draft_node")
    assert callable(graphs.run_review_graph)
    assert callable(graphs.graph_thread_id)
    assert callable(graphs.assert_resumable)


def test_old_generated_route_contract_is_removed_but_reads_and_decisions_remain():
    schema = create_app().openapi()
    assert "/api/v1/plan-changes/generate" not in schema["paths"]
    assert "GeneratedPlanChangeRequest" not in schema["components"]["schemas"]
    for path in ("/api/v1/plans/generate", "/api/v1/plans/current",
                 "/api/v1/plan-changes/{proposal_id}/confirm",
                 "/api/v1/plan-changes/{proposal_id}/cancel"):
        assert path in schema["paths"]
    assert {"target", "scope", "desired_depth", "starting_point", "outcome_purpose", "constraints"} <= set(GoalSpec.model_fields)


def test_application_does_not_import_retained_test_graph_or_fake_scenarios():
    root = Path(__file__).resolve().parents[2] / "app"
    forbidden = {"tests", "app.infrastructure.providers.planning_demo"}
    for file in root.rglob("*.py"):
        for node in ast.walk(ast.parse(file.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                assert not any(node.module == name or (node.module or "").startswith(name + ".") for name in forbidden), file
            elif isinstance(node, ast.Import):
                assert not any(a.name == name or a.name.startswith(name + ".") for a in node.names for name in forbidden), file


def test_nonplanning_import_smoke():
    for module in ("app.infrastructure.db.browser_auth", "app.infrastructure.db.workspace",
                   "app.application.assistant", "app.application.summaries", "app.application.prompts",
                   "app.application.learning_resources", "app.infrastructure.resources.github",
                   "app.infrastructure.resources.tavily", "app.infrastructure.providers.endpoint_policy"):
        assert importlib.import_module(module)
