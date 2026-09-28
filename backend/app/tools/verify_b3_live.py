"""Real paid B3 verification on a NEW verification project and localhost HTTP socket.

Uses the configured cloud provider without Fake or automatic redispatch. Retains
run/attempt/plan/checkpoint evidence in the dedicated local B3 databases.
"""
import json
import secrets
import socket
import threading
import time
from dataclasses import replace

import httpx
import psycopg
import uvicorn
from app.composition import build_container
from app.core.config import get_settings
from app.core.ids import new_id
from app.infrastructure.db.plan_repository import to_psycopg_dsn
from app.main import create_app


def main():
    import os
    settings = get_settings()
    if settings.llm_provider != "openai_compatible" or not settings.llm_api_key or not settings.llm_model_id:
        raise SystemExit("B3 live verification pending: fill LLM_BASE_URL, LLM_MODEL_ID, LLM_API_KEY in D:\\studyplan\\.env")
    project_id = new_id("prj")
    token = secrets.token_urlsafe(32)
    settings = replace(settings,local_project_id=project_id,local_session_token=token)
    container = build_container(settings)
    with psycopg.connect(to_psycopg_dsn(os.environ["STUDYPLAN_MIGRATION_DSN"])) as conn:
        conn.execute("INSERT INTO learning_projects(project_id,owner_actor_id,title,goal_statement,stable_key) VALUES (%s,%s,'B3 live verification','Python text CLI',%s)",
                     (project_id,settings.local_actor_id,"live." + project_id))
    sock = socket.socket()
    sock.bind(("127.0.0.1",0))
    sock.listen(32)
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(container),host="127.0.0.1",port=port,log_level="error",access_log=False))
    thread = threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True)
    thread.start()
    try:
        for _ in range(100):
            if server.started:
                break
            if not thread.is_alive():
                raise RuntimeError("HTTP server failed to start")
            time.sleep(0.02)
        if not server.started:
            raise RuntimeError("HTTP server readiness timed out")
        with httpx.Client(base_url=f"http://127.0.0.1:{port}",timeout=settings.llm_timeout_seconds*6+30) as client:
            response = client.post("/api/v1/session",json={"token":token})
            response.raise_for_status()
            params={"project_id":project_id}
            response=client.post("/api/v1/plans/generate",params=params,json={"goal":"学会使用 Python 编写一个读入文本并输出统计报告的命令行工具，具备文件异常处理和可复现运行说明"})
            response.raise_for_status()
            run_id=response.json()["run_id"]
            response=client.get(f"/api/v1/runs/{run_id}",params=params)
            response.raise_for_status()
            run=response.json()
            if run["status"] != "waiting_user":
                print(json.dumps({"run_id":run_id,"status":run["status"],"next_action":run["next_action"]}))
                raise SystemExit("Live generation did not produce a reviewable draft; no automatic retry")
            draft=client.get(f"/api/v1/plans/drafts/{run['result_ref']}",params=params).json()
            command={"decision":"approve","expected_version":0,"draft_hash":draft["draft_hash"],"idempotency_key":"live-"+run_id}
            response=client.post(f"/api/v1/plans/drafts/{draft['draft_id']}/decision",params=params,json=command)
            response.raise_for_status()
            plan=response.json()["plan"]
            response=client.get("/api/v1/plans/current",params=params)
            response.raise_for_status()
            assert response.json()["plan_id"] == plan["plan_id"]
            response=client.post(f"/api/v1/plans/drafts/{draft['draft_id']}/decision",params=params,json=command)
            response.raise_for_status()
            assert response.json()["plan"]["plan_id"] == plan["plan_id"]
            final=client.get(f"/api/v1/runs/{run_id}",params=params).json()
            assert final["status"] == "succeeded",final
        record=container.plan_service._runs.get_run(project_id=project_id,run_id=run_id)
        from app.agent_workflows.runtime import PostgresSaver
        with PostgresSaver.from_conn_string(to_psycopg_dsn(settings.checkpoint_database_url)) as saver:
            saved=saver.get_tuple({"configurable":{"thread_id":record.thread_id}})
            assert saved and saved.checkpoint["channel_values"]["result_id"] == plan["plan_id"]
        with psycopg.connect(to_psycopg_dsn(os.environ["STUDYPLAN_MIGRATION_DSN"])) as conn:
            rows=conn.execute("SELECT model_id,status,input_tokens,output_tokens,schema_name FROM ai_provider_attempts WHERE run_id=%s ORDER BY created_at",(run_id,)).fetchall()
        assert rows and all(row[1] == "succeeded" for row in rows),rows
        print(json.dumps({"verified":"real_provider_HTTP_PG_StateGraph_checkpoint_publish_replay",
                          "project_id":project_id,"run_id":run_id,"plan_id":plan["plan_id"],
                          "revision":plan["revision"],"attempts":rows},ensure_ascii=False))
    finally:
        server.should_exit=True
        thread.join(timeout=15)
        sock.close()


if __name__ == "__main__":
    main()
