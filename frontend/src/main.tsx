import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api, ApiError } from "./api/client";
import type { components } from "./api/generated/schema";
import "./style.css";

type DTO = components["schemas"];
type Draft = DTO["PlanDraftView"];
type Stage = DTO["StageDetail"];
type Plan = DTO["PlanView"];

function Resources({ items }: { items: Draft["stage_resources"] }) {
  return <div className="resources">{(items ?? []).map(item => <div key={item.assignment_id}>
    {(item.ordered_sections ?? []).length > 0 && <><p className="resource-label">主线资料 · {item.creator}</p>
      <ol>{(item.ordered_sections ?? []).map(section => <li key={section.section_id}>
        <a href={section.url} target="_blank" rel="noreferrer">{section.title}</a>
      </li>)}</ol></>}
    {(item.fallback_search_terms ?? []).length > 0 && <p>待查找资料：{(item.fallback_search_terms ?? []).join("；")}</p>}
  </div>)}</div>;
}

function App() {
  const [projects, setProjects] = useState<string[]>([]);
  const [project, setProject] = useState("");
  const [token, setToken] = useState("");
  const [goal, setGoal] = useState("学会使用 Python 编写一个可验收的文本统计命令行工具");
  const [run, setRun] = useState<DTO["RunView"] | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [stages, setStages] = useState<Stage[]>([]);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [checkingSession, setCheckingSession] = useState(true);
  const remember = (list: string[]) => { setProjects(list); setProject(list[0] ?? ""); };
  useEffect(() => { api.session().then(s => remember(s.project_ids)).catch(() => {}).finally(() => setCheckingSession(false)); }, []);
  async function loadDraft(id: string) {
    const value = await api.draft(project, id); setDraft(value); setStages(value.stages ?? []); return value;
  }
  async function loadRun(id: string) {
    const value = await api.run(project, id); setRun(value);
    if (value.next_action === "review_draft" && value.result_ref) await loadDraft(value.result_ref);
    return value;
  }
  useEffect(() => {
    if (!project) return;
    setDraft(null); setRun(null); setPlan(null);
    api.current(project).then(setPlan).catch(err => { if (!(err instanceof ApiError && err.status === 404)) setError(err.message); });
    const id = localStorage.getItem(`studyplan-run:${project}`);
    if (id) loadRun(id).catch(err => setError(err.message));
  }, [project]);
  useEffect(() => {
    if (!run || !["queued", "running"].includes(run.status)) return;
    const timer = setTimeout(() => { loadRun(run.run_id).catch(err => setError(err.message)); }, 1500);
    return () => clearTimeout(timer);
  }, [run, project]);
  async function act(action: () => Promise<void>) {
    setBusy(true); setError(""); setNotice("");
    try { await action(); } catch (err) { setError(err instanceof Error ? err.message : "操作失败"); }
    finally { setBusy(false); }
  }
  const dirty = !!draft && JSON.stringify(stages) !== JSON.stringify(draft.stages ?? []);
  async function decide(decision: DTO["DraftDecisionRequest"]["decision"]) {
    if (!draft) return;
    let key = localStorage.getItem(`studyplan-confirm:${draft.draft_id}:${draft.draft_hash}`);
    if (!key) { key = crypto.randomUUID(); localStorage.setItem(`studyplan-confirm:${draft.draft_id}:${draft.draft_hash}`, key); }
    try {
      const result = await api.decide(project, draft.draft_id, {
        decision, expected_version: plan?.revision ?? 0, draft_hash: draft.draft_hash,
        idempotency_key: decision === "approve" ? key : "",
        edited_stages: decision === "edit" ? stages : null,
      });
      setDraft(result.draft); setStages(result.draft.stages ?? []);
      if (result.plan) setPlan(result.plan);
      await loadRun(result.run_id);
      setNotice(decision === "edit" ? "修改已保存，请重新查看后确认。" : decision === "approve" ? "路线已确认并保存。" : "草案已取消，已确认路线保留。");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        await loadDraft(draft.draft_id); setPlan(await api.current(project));
        throw new Error("草案或路线已被其他窗口修改。已加载最新内容，请重新检查。");
      }
      throw err;
    }
  }
  function change(index: number, field: "title" | "objective", value: string) {
    setStages(old => old.map((stage, i) => i === index ? { ...stage, [field]: value } : stage));
  }
  function move(index: number, delta: number) {
    setStages(old => {
      const next = [...old]; [next[index], next[index + delta]] = [next[index + delta], next[index]];
      return next.map((stage, order_index) => ({ ...stage, order_index }));
    });
  }
  const editable = draft?.status === "awaiting_approval";
  return <main>
    <header><a className="wordmark" href="/">学习规划</a><span>把学习目标变成可验收的路线</span></header>
    <div className="workspace">
      <aside>
        <h1>下一步，学什么？</h1>
        <p className="intro">先生成草案，调整阶段与目标，再确认自己的学习路线。</p>
        {checkingSession ? <p>正在读取会话…</p> : projects.length === 0 ? <form onSubmit={e => { e.preventDefault(); act(async () => { const value = await api.enter(token); remember(value.project_ids); setToken(""); }); }}>
          <label htmlFor="token">本地访问口令</label><input id="token" type="password" autoComplete="off" value={token} onChange={e => setToken(e.target.value)} required />
          <button disabled={busy}>进入学习空间</button>
        </form> : <>
          {projects.length > 1 && <label>学习空间<select value={project} onChange={e => setProject(e.target.value)}>{projects.map(p => <option key={p}>{p}</option>)}</select></label>}
          <form onSubmit={e => { e.preventDefault(); act(async () => {
            const result = await api.generate(project, goal); localStorage.setItem(`studyplan-run:${project}`, result.run_id);
            await loadRun(result.run_id);
          }); }}>
            <label htmlFor="goal">学习目标</label><textarea id="goal" rows={5} maxLength={2000} value={goal} onChange={e => setGoal(e.target.value)} required />
            <button disabled={busy || !goal.trim() || run?.status === "reconciliation_required"}>{busy ? "正在处理…" : "生成学习草案"}</button>
          </form>
          <p className="scope-note">当前内容包：Python 工程入门。主线引用官方教程，适合已有基础编程认知的学习者。</p>
        </>}
        {run && <div className="run-state" role="status">
          {run.next_action === "review_draft" ? "草案已生成，等待你检查与确认。" : run.next_action === "reconcile" ? "本次运行需要核对，请勿重复发起模型调用。" : run.status === "failed" ? "生成失败，可以检查配置后重新发起。" : run.status === "succeeded" ? "路线已保存。" : run.status === "cancelled" ? "本次草案已取消。" : "正在生成草案…"}
          {run.error && <p>{run.error.message}</p>}
          <button className="quiet" disabled={busy} onClick={() => act(async () => { await loadRun(run.run_id); setPlan(await api.current(project)); })}>刷新运行状态</button>
        </div>}
        {error && <p className="error" role="alert">{error}</p>}
        {notice && <p className="notice" role="status">{notice}</p>}
      </aside>
      <section className="route-area">
        {draft ? <>
          <div className="section-heading"><h2>{editable ? "检查你的草案" : draft.status === "approved" ? "已确认草案" : "已取消草案"}</h2><span>候选版本 {draft.revision}</span></div>
          <p className="hint">阶段按顺序推进。可调整标题、目标和顺序；保存修改后再确认。</p>
          <ol className="stages">{stages.map((stage, index) => <li key={stage.stage_id}>
            <div className="stage-top"><span className="step">{index + 1}</span>{editable ? <input aria-label={`阶段 ${index + 1} 标题`} value={stage.title} onChange={e => change(index,"title",e.target.value)} /> : <h3>{stage.title}</h3>}
              {editable && <div className="order-actions"><button className="quiet" aria-label={`阶段 ${index + 1} 上移`} disabled={busy || index === 0} onClick={() => move(index,-1)}>上移</button><button className="quiet" aria-label={`阶段 ${index + 1} 下移`} disabled={busy || index === stages.length - 1} onClick={() => move(index,1)}>下移</button></div>}
            </div>
            {editable ? <textarea aria-label={`阶段 ${index + 1} 目标`} value={stage.objective} onChange={e => change(index,"objective",e.target.value)} rows={2} /> : <p>{stage.objective}</p>}
            <Resources items={(draft.stage_resources ?? []).filter(r => r.stage_id === stage.stage_id)} />
          </li>)}</ol>
          {editable && <div className="decision-actions"><button className="secondary" disabled={busy || !dirty} onClick={() => act(() => decide("edit"))}>保存修改</button><button disabled={busy || dirty} onClick={() => act(() => decide("approve"))}>确认并保存路线</button><button className="quiet" disabled={busy} onClick={() => act(() => decide("cancel"))}>取消草案</button>{dirty && <span>请先保存修改</span>}</div>}
        </> : !plan && <div className="empty"><h2>给目标一条清晰的路线</h2><p>填写你想学会的内容，草案会在这里展开。生成的内容需要你确认才会成为正式路线。</p></div>}
        {plan && <section className="confirmed"><div className="section-heading"><h2>当前正式路线</h2><span>版本 {plan.revision}</span></div><p>{plan.goal_snapshot}</p><ol>{(plan.stages ?? []).map(stage => <li key={stage.stage_id}><h3>{stage.title}</h3><p>{stage.objective}</p><Resources items={(plan.stage_resources ?? []).filter(r => r.stage_id === stage.stage_id)} /></li>)}</ol></section>}
      </section>
    </div>
  </main>;
}
const root = document.getElementById("root");
if (root) createRoot(root).render(<React.StrictMode><App /></React.StrictMode>);
