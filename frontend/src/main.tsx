import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api, ApiError, setCsrfToken } from "./api/client";
import type { DTO, Page } from "./api/types";
import { AuthPage } from "./features/auth/AuthPage";
import { AppShell } from "./components/AppShell";
import { LearningDashboard } from "./features/learning/LearningDashboard";
import { LearningPath } from "./features/learning/LearningPath";
import { MainWorkspace } from "./features/learning/MainWorkspace";
import { clearResourceBuffers } from "./features/learning/resourceBuffer";
import {
  ConversationList,
  SummaryDetail,
  PracticeDetail,
} from "./features/learning/SupportingPages";
import { PlanningPage } from "./features/planning/PlanningPage";
import { ModelSettings } from "./ModelSettings";
import "./style.css";
import {useAssistant} from "./features/learning/useAssistant";
import {stagePage} from "./components/learningNavigation";
import type {PracticeTaskIntent} from "./components/learningNavigation";

const pages: Page[] = [
  "dashboard",
  "planning",
  "path",
  "workspace",
  "summary",
  "practice",
  "conversations",
  "settings",
];
function App() {
  const [session, setSession] = useState<DTO["SessionView"] | null>(null),
    [loading, setLoading] = useState(true);
  const [workspace, setWorkspace] = useState<
      DTO["LearningWorkspaceView"] | null
    >(null),
    [error, setError] = useState("");
  const [page, setPage] = useState<Page>(() =>
    pages.includes(location.hash.slice(1) as Page)
      ? (location.hash.slice(1) as Page)
      : "dashboard",
  );
  const [position, setPosition] = useState({ stage: "", node: "", storageKey: "" });
  const [artifactRefreshVersion,setArtifactRefreshVersion]=useState(0);
  const [taskIntent, setTaskIntent] = useState<PracticeTaskIntent>();
  const [fake, setFake] = useState<boolean | null>(null);
  const stageId = position.stage, nodeId = position.node;
  const project = session?.project_ids[0] || "";
  const positionKey = workspace ? `studyplan-position:${session?.username}:${project}:${workspace.plan.revision}` : "";
  function navigate(p: Page) {
    location.hash = p;
    setPage(p);
  }
  function accept(s: DTO["SessionView"]) {
    setCsrfToken(s.csrf_token || "");
    setSession(s);
  }
  useEffect(() => {
    api
      .session()
      .then(accept)
      .catch((e) => {
        if (!(e instanceof ApiError && e.status === 401)) setError(e.message);
      })
      .finally(() => setLoading(false));
    api
      .health()
      .then((h) => setFake(h.fake_llm))
      .catch((e) => setError(e.message));
    const onHash = () => {
      const p = location.hash.slice(1) as Page;
      setPage(pages.includes(p) ? p : "dashboard");
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  async function refresh() {
    if (project) setWorkspace(await api.workspace(project));
  }
  useEffect(() => {
    setWorkspace(null);
    setPosition({ stage: "", node: "", storageKey: "" });
    if (project) refresh().catch((e) => setError(e.message));
  }, [project]);
  useEffect(() => {
    if (!workspace) return;
    let saved: { stage: string; node: string } | null = null;
    try {
      saved = JSON.parse(localStorage.getItem(positionKey) || localStorage.getItem(`studyplan-position:${project}:${workspace.plan.revision}`) || "null");
    } catch {}
    const stage =
      workspace.stages.find((s) => s.stage.stage_id === saved?.stage) ||
      workspace.stages[0];
    setPosition({ stage: stage?.stage.stage_id || "", storageKey: positionKey,
      node: stage?.nodes.find((n) => n.node_id === saved?.node)?.node_id || stage?.nodes[0]?.node_id || "" });
  }, [workspace, project, positionKey]);
  useEffect(() => {
    if (workspace && stageId && position.storageKey === positionKey &&
        workspace.stages.some(s => s.stage.stage_id === stageId && (!nodeId || s.nodes.some(n => n.node_id === nodeId))))
      localStorage.setItem(
        positionKey,
        JSON.stringify({ stage: stageId, node: nodeId }),
      );
  }, [stageId, nodeId, workspace, positionKey, position.storageKey]);
  const assistant = useAssistant(project, session?.username || session?.csrf_token || "", async()=>{setArtifactRefreshVersion(v=>v+1);await refresh();}, workspace?.plan.plan_id);
  const stage = workspace?.stages.find((s) => s.stage.stage_id === stageId);
  function selectStage(id: string, external = false) {
    setPosition({ storageKey: positionKey, stage: id,
      node: id === stageId ? nodeId : workspace?.stages.find((s) => s.stage.stage_id === id)?.nodes[0]?.node_id || "" });
    navigate(stagePage(page, external));
  }
  function selectTask(stageId: string, taskId: string) {
    const selected = workspace?.stages.find(s => s.stage.stage_id === stageId);
    if (!selected?.tasks.some(task => task.task_id === taskId)) return;
    selectStage(stageId);
    setTaskIntent(old => ({ stageId, taskId, sequence: (old?.sequence || 0) + 1 }));
    navigate("practice");
  }
  function selectNode(id: string) {
    const owner = workspace?.stages.find(s => s.nodes.some(n => n.node_id === id));
    if (owner) setPosition({ storageKey: positionKey, stage: owner.stage.stage_id, node: id });
  }
  async function logout() {
    try {
      await api.logout();
      clearResourceBuffers();
      assistant.clear();
      setSession(null);
      setWorkspace(null);
      setCsrfToken("");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  if (loading) return <div className="loading">正在恢复学习空间…</div>;
  if (!session)
    return (
      <>
        <AuthPage onLogin={accept} />
        {error && (
          <div className="global-error" role="alert">
            {error}
            <button onClick={() => location.reload()}>重新加载</button>
          </div>
        )}
      </>
    );
  return (
    <AppShell
      page={page}
      assistant={assistant}
      navigate={navigate}
      session={session}
      workspace={workspace}
      stageId={stageId}
      nodeId={nodeId}
      selectStage={selectStage}
      selectNode={selectNode}
      selectTask={selectTask}
      logout={logout}
    >
      {error && (
        <div className="error" role="alert">
          {error}
          <button
            className="text-button"
            onClick={() => {
              setError("");
              refresh().catch((e) => setError(e.message));
            }}
          >
            重新加载
          </button>
        </div>
      )}
      {page === "dashboard" && (
        <LearningDashboard
          workspace={workspace}
          stageId={stageId}
          navigate={navigate}
          enterStage={id => selectStage(id, true)}
        />
      )}
      {page === "planning" && (
        <PlanningPage key={`${session.username}:${project}`} project={project} actorKey={session.username || ''} onPublished={refresh} />
      )}
      {page === "path" && (
        <LearningPath
          workspace={workspace}
          enterStage={id => selectStage(id, true)}
          create={() => navigate("planning")}
        />
      )}
      {page === "workspace" && (
        <MainWorkspace
          actorKey={session.username || session.csrf_token || 'development-session'}
          projectId={project}
          planId={workspace?.plan.plan_id || ''}
          planRevision={workspace?.plan.revision || 0}
          plan={workspace?.plan}
          introducedNodeIds={workspace?.stages.filter(item => item.stage.order_index < (stage?.stage.order_index ?? 0)).flatMap(item => item.nodes.map(node => node.node_id)) || []}
          onPublished={refresh}
          stage={stage}
          nodeId={nodeId}
          allNodes={workspace?.stages.flatMap((s) => s.nodes) || []}
          selectNode={selectNode}
          create={() => navigate("planning")}
          practice={() => navigate("practice")} summary={() => {if(workspace&&stage)void assistant.start({plan_id:workspace.plan.plan_id,stage_id:stage.stage.stage_id,mode:"summary",task_id:null});}}
          startPractice={taskId=>{if(workspace&&stage)void assistant.start({plan_id:workspace.plan.plan_id,stage_id:stage.stage.stage_id,mode:"practice",task_id:taskId});}}
        />
      )}
      <div hidden={page !== 'summary'}><SummaryDetail key={project} project={project}
        workspace={workspace} artifactRefreshVersion={artifactRefreshVersion} initialStage={stageId} onStageChange={selectStage} active={page === 'summary'} onSaved={refresh} onStart={id=>{if(workspace)void assistant.start({plan_id:workspace.plan.plan_id,stage_id:id,mode:'summary',task_id:null});}} assistantBusy={assistant.starting||!!assistant.startPending}/></div>
      <div hidden={page !== 'practice'}><PracticeDetail key={project} project={project}
        workspace={workspace} artifactRefreshVersion={artifactRefreshVersion} initialStage={stageId} onStageChange={selectStage} active={page === 'practice'} onPublished={refresh} taskIntent={taskIntent} onStart={(stageId,taskId)=>{if(workspace)void assistant.start({plan_id:workspace.plan.plan_id,stage_id:stageId,mode:'practice',task_id:taskId});}} assistantBusy={assistant.starting||!!assistant.startPending}/></div>
      {page === "conversations" && <ConversationList controller={assistant} />}
      {page === "settings" && (
        <div className="content">
          <p className="eyebrow">MODEL SETTINGS</p>
          <h1>个人模型设置</h1>
          <p className="lede">保留现有的 OpenAI 兼容模型配置。</p>
          {fake === true && (
            <p className="notice">
              当前服务为 Fake LLM
              本地演示模式，不调用云模型。配置仅在真实模型模式生效。
            </p>
          )}
          <div className="panel">
            <ModelSettings onChange={() => {}} />
          </div>
        </div>
      )}
    </AppShell>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
