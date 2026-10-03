import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../../api/client";
import type { DTO } from "../../api/types";
import { Resources } from "../../components/Resources";
import { PlanChanges } from './PlanChanges';
import { LearningGuidance } from '../learning/LearningGuidance';

const DEPTH_LABELS: Record<DTO['GoalSpec']['desired_depth'], string> = {
  unspecified: '暂不指定', foundation: '建立基础', applied: '能够应用', deep: '深入理解',
};
const PURPOSE_LABELS: Record<DTO['GoalSpec']['outcome_purpose'], string> = {
  learn: '学习理解', interview: '面试准备', portfolio: '作品集', internship: '实习准备', production: '实际项目应用',
};

function GoalSpecSnapshot({ value }: { value: DTO['PlanDraftView']['goal_spec'] }) {
  if (!value) return null;
  return <section className="panel" aria-label="草案目标快照">
    <h3>本草案的目标与起点</h3>
    <p><strong>目标：</strong>{value.target}</p>
    <p><strong>期望深度：</strong>{DEPTH_LABELS[value.desired_depth ?? 'unspecified']}</p>
    <p><strong>成果用途：</strong>{PURPOSE_LABELS[value.outcome_purpose ?? 'learn']}</p>
    <p><strong>当前起点（自述）：</strong>{value.starting_point || '未补充'}</p>
    {!!value.scope?.length && <><strong>学习范围</strong><ul>{value.scope.map((item, index) => <li key={index}>{item}</li>)}</ul></>}
    {!!value.constraints?.length && <><strong>限制条件</strong><ul>{value.constraints.map((item, index) => <li key={index}>{item}</li>)}</ul></>}
  </section>;
}

//: 分批生成阶段 → 面向用户的说明。只使用后端业务 DTO 的闭集枚举，不映射任何图内部名称。
const PROGRESS_PHASE_LABELS: Record<DTO["RunProgress"]["phase"], string> = {
  outline: "正在生成路线骨架",
  structure: "正在生成阶段知识结构",
  practice: "正在生成阶段实践任务",
  validation: "正在合并并校验草案",
  done: "草案已生成",
};

const KNOWN_RUN_STATUSES = new Set<string>([
  "queued", "running", "waiting_user", "succeeded", "failed", "cancelled", "reconciliation_required",
]);
const KNOWN_RUN_ACTIONS = new Set<string>(["none", "review_draft", "retry", "reconcile", "wait"]);

function runNeedsCheck(run: DTO["RunView"]): boolean {
  if (!KNOWN_RUN_STATUSES.has(run.status) || !KNOWN_RUN_ACTIONS.has(run.next_action)) return true;
  switch (run.status) {
    case "queued":
    case "running": return run.next_action !== "wait";
    case "waiting_user": return run.next_action !== "review_draft";
    case "succeeded": return run.next_action !== "none" && !(run.next_action === "review_draft" && !!run.result_ref);
    case "failed": return run.next_action !== "retry" && run.next_action !== "none";
    case "cancelled": return run.next_action !== "none";
    case "reconciliation_required": return run.next_action !== "reconcile";
    default: return true;
  }
}

function canStartNewRun(run: DTO["RunView"] | null): boolean {
  if (!run) return true;
  if (runNeedsCheck(run)) return false;
  return (run.status === "succeeded" && run.next_action === "none") ||
    (run.status === "failed" && (run.next_action === "retry" || run.next_action === "none")) ||
    (run.status === "cancelled" && run.next_action === "none");
}

function RunProgressPanel({ progress }: { progress: DTO["RunProgress"] }) {
  const totalBatches =
    progress.total_structure_batches + progress.total_practice_batches;
  const percent =
    totalBatches > 0
      ? Math.min(
          100,
          Math.round((progress.completed_batches / totalBatches) * 100),
        )
      : progress.phase === "done"
        ? 100
        : 0;
  const stageLabel =
    progress.current_stage_index !== null &&
    progress.current_stage_index !== undefined
      ? `阶段 ${progress.current_stage_index + 1} / ${progress.total_stages}` +
        (progress.current_stage_title
          ? ` · ${progress.current_stage_title}`
          : "")
      : `共 ${progress.total_stages} 个阶段`;
  const usage =
    progress.usage_complete &&
    progress.input_tokens !== null &&
    progress.output_tokens !== null
      ? `模型计量：输入 ${progress.input_tokens} · 输出 ${progress.output_tokens}`
      : "模型计量：尚未完整上报";
  return (
    <div className="run-progress" aria-label="生成进度">
      <div className="run-progress-head">
        <strong>{PROGRESS_PHASE_LABELS[progress.phase]}</strong>
        <span className="pill">{stageLabel}</span>
      </div>
      <div
        className="progress-track"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <span style={{ width: `${percent}%` }} />
      </div>
      <p className="form-note">
        已完成 {progress.completed_batches} / {totalBatches} 个批次（结构{" "}
        {progress.completed_structure_batches}/
        {progress.total_structure_batches} · 实践{" "}
        {progress.completed_practice_batches}/{progress.total_practice_batches}）
      </p>
      <p className="form-note">
        模型请求 {progress.request_count} / {progress.max_requests} · {usage}
      </p>
      {progress.failure_stage && (
        <p className="form-note">
          失败位置：{progress.failure_phase === "practice" ? "实践" : "结构"}批次{" "}
          {progress.failure_stage}
        </p>
      )}
    </div>
  );
}

type PendingCancellation = { run_id: string; body: DTO['RunCancelRequest']; conflict?: boolean };

export function PlanningPage({
  project,
  actorKey,
  onPublished,
  fake,
}: {
  project: string;
  actorKey: string;
  onPublished: () => Promise<void>;
  fake: boolean | null;
}) {
  const [goal, setGoal] = useState("学习 Agent 开发，完成一个可验收的知识助手");
  const [depth, setDepth] = useState<DTO['GoalSpec']['desired_depth']>('unspecified');
  const [purpose, setPurpose] = useState<DTO['GoalSpec']['outcome_purpose']>('learn');
  const [startingPoint, setStartingPoint] = useState('');
  const [scopeInput, setScopeInput] = useState('');
  const [constraintsInput, setConstraintsInput] = useState('');
  const [run, setRun] = useState<DTO["RunView"] | null>(null),
    [draft, setDraft] = useState<DTO["PlanDraftView"] | null>(null);
  const [stages, setStages] = useState<DTO["StageDetail"][]>([]),
    [baseVersion, setBaseVersion] = useState(0);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [conflict, setConflict] = useState(false),
    [notice, setNotice] = useState("");
  const cancelStorage = `studyplan-cancel:${JSON.stringify([actorKey, project])}`;
  const [pendingCancellation, setPendingCancellation] = useState<PendingCancellation | null>(null);
  const cancellationRef = useRef<PendingCancellation | null>(null);
  function rememberCancellation(value: PendingCancellation | null) {
    cancellationRef.current = value;
    setPendingCancellation(value);
    if (value) localStorage.setItem(cancelStorage, JSON.stringify(value));
    else localStorage.removeItem(cancelStorage);
  }
  const generating = useRef(false);
  const loadedDraft = useRef<string | null>(null);
  const detailScope = JSON.stringify([actorKey, project]);
  const currentDetailScope = useRef(detailScope);
  currentDetailScope.current = detailScope;
  const mounted = useRef(false);
  const runReadSequence = useRef(0);
  const draftReadSequence = useRef(0);
  const actionSequence = useRef(0);
  const [pollAttempt, setPollAttempt] = useState(0);
  const [acceptedRun, setAcceptedRun] = useState(false);
  const [pendingPlanChange, setPendingPlanChange] = useState(false);
  const [planChangeSubmitting, setPlanChangeSubmitting] = useState(false);
  const [pendingRunId, setPendingRunId] = useState<string | null>(null);
  const [historyRuns, setHistoryRuns] = useState<DTO['RunView'][]>([]);
  const [historyRunsScope, setHistoryRunsScope] = useState<string | null>(null);
  const [historyOpened, setHistoryOpened] = useState(false);
  const [historyBusy, setHistoryBusy] = useState(false);
  const [historyError, setHistoryError] = useState('');
  const [pendingHistorySelection, setPendingHistorySelection] = useState<string | null>(null);
  const runHistoryScope = JSON.stringify([actorKey, project]);
  const currentRunHistoryScope = useRef(runHistoryScope);
  currentRunHistoryScope.current = runHistoryScope;
  const historyReadSequence = useRef(0);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      runReadSequence.current++;
      draftReadSequence.current++;
      historyReadSequence.current++;
    };
  }, []);
  useEffect(() => {
    runReadSequence.current++;
    draftReadSequence.current++;
    actionSequence.current++;
    generating.current = false;
    loadedDraft.current = null;
    cancellationRef.current = null;
    setPendingCancellation(null);
    setRun(null);
    setDraft(null);
    setStages([]);
    setBaseVersion(0);
    setPendingRunId(null);
    setAcceptedRun(false);
    setBusy(false);
    setPendingPlanChange(false);
    setPlanChangeSubmitting(false);
    setConflict(false);
    setNotice('');
    setError('');
  }, [detailScope]);
  const generationLifecycleBlocked = busy || !!pendingCancellation || acceptedRun || !canStartNewRun(run) || fake === null ||
    pendingPlanChange || planChangeSubmitting ||
    draft?.status === "awaiting_approval" ||
    run?.status === "queued" || run?.status === "running" ||
    run?.status === "reconciliation_required";
  const generationBlocked = generationLifecycleBlocked || !goal.trim();
  useEffect(() => {
    historyReadSequence.current++;
    setHistoryRuns([]);
    setHistoryRunsScope(null);
    setHistoryOpened(false);
    setHistoryBusy(false);
    setHistoryError('');
    setPendingHistorySelection(null);
  }, [runHistoryScope]);
  useEffect(() => () => { historyReadSequence.current++; }, []);
  async function loadDraft(id: string, force = false) {
    // Status polling must never replace the user's editable snapshot or its base version.
    if (!force && loadedDraft.current === id) return;
    const scope = detailScope;
    const sequence = ++draftReadSequence.current;
    const isCurrent = () => mounted.current && currentDetailScope.current === scope && draftReadSequence.current === sequence;
    let d: DTO['PlanDraftView'];
    try {
      d = await api.draft(project, id);
    } catch (e) {
      if (!isCurrent()) return;
      throw e;
    }
    if (!isCurrent()) return;
    let current: DTO['PlanView'] | null;
    try {
      current = await api.current(project);
    } catch (e) {
      if (!isCurrent()) return;
      throw e;
    }
    if (!isCurrent()) return;
    loadedDraft.current = id;
    setDraft(d);
    setStages(d.stages ?? []);
    setBaseVersion(current?.revision ?? 0);
  }
  async function loadRun(id: string) {
    const scope = detailScope;
    const sequence = ++runReadSequence.current;
    draftReadSequence.current++;
    const isCurrent = () => mounted.current && currentDetailScope.current === scope && runReadSequence.current === sequence;
    let r: DTO['RunView'];
    try {
      r = await api.run(project, id);
    } catch (e) {
      if (!isCurrent()) return;
      throw e;
    }
    if (!isCurrent()) return;
    const pending = cancellationRef.current;
    if (pending?.run_id === id && (pending.conflict || r.version !== pending.body.expected_version ||
        !['queued', 'running'].includes(r.status) || runNeedsCheck(r))) rememberCancellation(null);
    setRun(r);
    setPendingRunId(null);
    const readingResult = !runNeedsCheck(r) && !!r.result_ref &&
      (r.next_action === "review_draft" || r.status === "succeeded");
    setAcceptedRun(!canStartNewRun(r) || readingResult);
    if (readingResult && r.result_ref) {
      let resultVerified = false;
      try {
        await loadDraft(r.result_ref);
        resultVerified = loadedDraft.current === r.result_ref;
      } catch (e) {
        // Historical successful Runs reference a plan. Resolve it by API identity,
        // without assuming the opaque result_ref has a particular prefix.
        if (!isCurrent()) return;
        if (!(e instanceof ApiError && e.status === 404)) throw e;
        let current: DTO['PlanView'] | null;
        try {
          current = await api.current(project);
        } catch (currentError) {
          if (!isCurrent()) return;
          throw currentError;
        }
        if (!isCurrent()) return;
        if (current?.plan_id !== r.result_ref) throw e;
        resultVerified = true;
      }
      if (isCurrent() && resultVerified) setAcceptedRun(false);
    }
  }
  async function readServerRuns() {
    const scope = runHistoryScope;
    const sequence = ++historyReadSequence.current;
    setHistoryBusy(true);
    setHistoryError('');
    try {
      const result = await api.runs(project, 20);
      if (currentRunHistoryScope.current !== scope || historyReadSequence.current !== sequence) return;
      setHistoryRuns(result);
      setHistoryRunsScope(scope);
      setHistoryOpened(true);
    } catch (failure) {
      if (currentRunHistoryScope.current !== scope || historyReadSequence.current !== sequence) return;
      setHistoryError((failure as Error).message);
    } finally {
      if (currentRunHistoryScope.current === scope && historyReadSequence.current === sequence) setHistoryBusy(false);
    }
  }
  function statusLabel(status: string): string {
    const labels: Record<string, string> = {
      queued: '等待生成', running: '正在生成', waiting_user: '等待草案处理',
      succeeded: '已完成', failed: '生成失败', cancelled: '已取消',
      reconciliation_required: '需要核对',
    };
    return labels[status] ?? '未知状态，需要核对';
  }
  function runBlocksHistorySwitch(candidateId: string): boolean {
    if (pendingCancellation && pendingCancellation.run_id !== candidateId) return true;
    if (pendingRunId && !run && pendingRunId !== candidateId) return true;
    if (run?.run_id === candidateId) return false;
    if (draft?.status === 'awaiting_approval') return true;
    if (acceptedRun && (!run || run.run_id !== candidateId)) return true;
    if (run && (runNeedsCheck(run) || ['queued', 'running', 'waiting_user', 'reconciliation_required'].includes(run.status))) return true;
    return false;
  }
  async function selectServerRun(id: string, discardEdits = false) {
    if (busy || historyBusy || runBlocksHistorySwitch(id)) return;
    if (run?.run_id === id) {
      setPendingHistorySelection(null);
      await act(() => loadRun(id));
      return;
    }
    if (dirty && !discardEdits) {
      setPendingHistorySelection(id);
      return;
    }
    setPendingHistorySelection(null);
    await act(() => acceptRun(id));
  }
  async function acceptRun(id: string) {
    const scope = detailScope;
    if (currentDetailScope.current !== scope) return;
    localStorage.setItem(`studyplan-run:${project}`, id);
    setPendingRunId(id);
    setRun(null);
    setAcceptedRun(true);
    setPollAttempt(0);
    loadedDraft.current = null;
    setDraft(null);
    setConflict(false);
    setNotice("");
    await loadRun(id);
  }
  async function generatePlanChange(body: DTO['GeneratedPlanChangeRequest']) {
    if (generationLifecycleBlocked || generating.current) throw new Error('当前运行或草案尚未完成核对，不能再次生成。');
    const scope = detailScope;
    generating.current = true;
    setPlanChangeSubmitting(true);
    try {
      const result = await api.generatePlanChange(project, body);
      if (!mounted.current || currentDetailScope.current !== scope) return;
      await acceptRun(result.run_id);
    } finally {
      if (mounted.current && currentDetailScope.current === scope) {
        generating.current = false;
        setPlanChangeSubmitting(false);
      }
    }
  }
  async function refreshPlanChangeDraft(preview: DTO['PlanChangePreviewView']) {
    const changedDraft = preview.draft;
    loadedDraft.current = changedDraft.draft_id;
    setDraft(changedDraft);
    setStages(changedDraft.stages ?? []);
    setBaseVersion(changedDraft.revision);
    setConflict(false);
    const decidedGoal = preview.status === 'approved' ? preview.after_goal : preview.before_goal;
    if (typeof decidedGoal === 'string') setGoal(decidedGoal);
    if (preview.status === 'approved' && preview.operation === 'change_goal') {
      setDepth('unspecified');
      setPurpose('learn');
      setStartingPoint('');
      setScopeInput('');
      setConstraintsInput('');
    }
  }
  useEffect(() => {
    const id = localStorage.getItem(`studyplan-run:${project}`);
    try {
      const saved = JSON.parse(localStorage.getItem(cancelStorage) || 'null') as PendingCancellation | null;
      if (saved?.run_id === id && Number.isInteger(saved.body?.expected_version) && saved.body.expected_version > 0 &&
          typeof saved.body.idempotency_key === 'string' && saved.body.idempotency_key.length > 0 && saved.body.idempotency_key.length <= 128) {
        cancellationRef.current = saved;
        setPendingCancellation(saved);
      }
    } catch { /* Keep restoring the Run when a local request record is unreadable. */ }
    if (id) {
      setPendingRunId(id);
      setAcceptedRun(true);
      loadRun(id).catch((e) => setError(e.message));
    }
  }, [detailScope]);
  useEffect(() => {
    if (pendingCancellation || !run || runNeedsCheck(run) || run.next_action !== "wait" || !["queued", "running"].includes(run.status)) return;
    const timer = setTimeout(
      () => loadRun(run.run_id).catch((e) => setError(e.message))
        .finally(() => setPollAttempt(n => n + 1)),
      document.hidden ? 30000 : Math.min(10000, 1500 * 1.5 ** pollAttempt),
    );
    return () => clearTimeout(timer);
  }, [run, pollAttempt, pendingCancellation]);
  async function cancelGeneration(retry = false) {
    if (busy || !run || runNeedsCheck(run) || run.next_action !== 'wait' || !['queued', 'running'].includes(run.status)) return;
    const scope = detailScope;
    const previous = cancellationRef.current;
    if (previous && (!retry || previous.conflict || previous.run_id !== run.run_id)) return;
    const pending: PendingCancellation = previous ?? {
      run_id: run.run_id, body: { expected_version: run.version, idempotency_key: crypto.randomUUID() },
    };
    runReadSequence.current++;
    draftReadSequence.current++;
    rememberCancellation(pending);
    await act(async () => {
      let result: DTO['RunView'];
      try {
        result = await api.cancelRun(project, pending.run_id, pending.body);
      } catch (failure) {
        if (!mounted.current || currentDetailScope.current !== scope) return;
        runReadSequence.current++;
        if (failure instanceof ApiError && failure.status === 409) rememberCancellation({ ...pending, conflict: true });
        throw failure;
      }
      if (!mounted.current || currentDetailScope.current !== scope) return;
      runReadSequence.current++;
      rememberCancellation(null);
      setRun(result);
      setAcceptedRun(!canStartNewRun(result));
      setNotice(result.status === 'reconciliation_required'
        ? '取消已登记，但已有请求可能发出，请核对运行结果；不能再次生成。'
        : '生成已取消。再次生成将创建一条新的运行。');
    });
  }
  async function act(fn: () => Promise<void>) {
    const scope = detailScope;
    const sequence = ++actionSequence.current;
    const isCurrent = () => mounted.current && currentDetailScope.current === scope && actionSequence.current === sequence;
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      if (isCurrent()) setError((e as Error).message);
    } finally {
      if (isCurrent()) setBusy(false);
    }
  }
  const dirty =
      !!draft && JSON.stringify(stages) !== JSON.stringify(draft.stages ?? []),
    editable = draft?.status === "awaiting_approval" && !draft.change_preview_id;
  function goalSpec(): DTO['GoalSpec'] | undefined {
    const scope = scopeInput.split(/\r?\n/).map(item => item.trim()).filter(Boolean);
    const constraints = constraintsInput.split(/\r?\n/).map(item => item.trim()).filter(Boolean);
    for (const [label, items] of [['学习范围', scope], ['限制条件', constraints]] as const) {
      if (items.length > 20 || items.some(item => Array.from(item).length > 300)) {
        throw new Error(`${label}最多填写 20 项，每项最多 300 个字符。`);
      }
    }
    const starting_point = startingPoint.trim();
    if (Array.from(starting_point).length > 1000) throw new Error('当前起点最多填写 1000 个字符。');
    if (depth === 'unspecified' && purpose === 'learn' && !starting_point && !scope.length && !constraints.length) return undefined;
    return { target: goal, scope, desired_depth: depth, starting_point, outcome_purpose: purpose, constraints };
  }
  async function decide(decision: DTO["DraftDecisionRequest"]["decision"]) {
    if (!draft) return;
    const storage = `studyplan-confirm:${draft.draft_id}:${draft.draft_hash}`;
    let key = localStorage.getItem(storage);
    if (!key) {
      key = crypto.randomUUID();
      localStorage.setItem(storage, key);
    }
    try {
      const r = await api.decide(project, draft.draft_id, {
        decision,
        expected_version: baseVersion,
        draft_hash: draft.draft_hash,
        idempotency_key: decision === "approve" ? key : "",
        edited_stages: decision === "edit" ? stages : null,
      });
      setDraft(r.draft);
      setStages(r.draft.stages ?? []);
      setNotice(
        decision === "approve"
          ? "路线已发布，可以进入阶段学习。"
          : decision === "edit"
            ? "修改已保存，请检查后确认。"
            : "草案已取消。",
      );
      setRun(await api.run(project, r.run_id));
      if (r.plan) await onPublished();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setConflict(true);
        throw new Error(
          "草案或正式路线已变更。请点击「重新加载草案」后检查内容；当前编辑尚未覆盖。",
        );
      }
      throw e;
    }
  }
  function change(i: number, field: "title" | "objective", value: string) {
    setStages((old) =>
      old.map((s, j) => (i === j ? { ...s, [field]: value } : s)),
    );
  }
  function move(i: number, delta: number) {
    setStages((old) => {
      const next = [...old];
      [next[i], next[i + delta]] = [next[i + delta], next[i]];
      return next.map((s, order_index) => ({ ...s, order_index }));
    });
  }
  return (
    <div className="content planning-content">
      <p className="eyebrow">BUILD YOUR LEARNING PLAN</p>
      <h1>从目标，到学习路线。</h1>
      <p className="lede">先生成完整草案，调整阶段，再确认自己的学习方向。</p>
      <section className="panel">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (generationBlocked || generating.current) return;
            generating.current = true;
            act(async () => {
              const result = await api.generate(project, goal, goalSpec());
              await acceptRun(result.run_id);
            }).finally(() => { generating.current = false; });
          }}
        >
          <label>
            你想学会什么？
            <textarea
              rows={3}
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              maxLength={2000}
              required
            />
          </label>
          <details>
            <summary>补充目标与起点（可选）</summary>
            <p className="form-note">这些信息用于调整路线与实践；当前起点按你的自述保存。未填写时继续按学习目标生成。</p>
            <label>期望深度<select value={depth} onChange={e => setDepth(e.target.value as DTO['GoalSpec']['desired_depth'])}>
              {Object.entries(DEPTH_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select></label>
            <label>成果用途<select value={purpose} onChange={e => setPurpose(e.target.value as DTO['GoalSpec']['outcome_purpose'])}>
              {Object.entries(PURPOSE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select></label>
            <label>当前起点<textarea rows={3} maxLength={1000} value={startingPoint} onChange={e => setStartingPoint(e.target.value)} placeholder="例如：有基础 Python，见过 Tool 概念，还未实现 dispatch。" /></label>
            <label>学习范围（每行一项）<textarea rows={3} value={scopeInput} onChange={e => setScopeInput(e.target.value)} placeholder="例如：Tool schema、Dispatch，分别写在一行。" /></label>
            <label>限制条件（每行一项）<textarea rows={3} value={constraintsInput} onChange={e => setConstraintsInput(e.target.value)} placeholder="例如：教程正文免费、每周三小时，分别写在一行。" /></label>
            <p className="form-note">学习范围与限制条件各最多 20 项，每项最多 300 个字符。</p>
          </details>
          <div className="section-heading">
            <p className="form-note">
              {fake === true
                ? "Fake LLM 本地演示 · 按领域蓝图生成，无云模型调用"
                : fake === false
                  ? "当前使用已有个人或部署模型配置 · 生成可能产生服务商费用"
                  : "正在读取模型运行模式…"}
            </p>
            <button
              className="btn primary"
              disabled={generationBlocked}
            >
              {busy ? "正在处理…" : "生成学习草案 →"}
            </button>
          </div>
        </form>
        <p className="form-note">可围绕 AI 全栈应用、Agent 应用开发或云服务提出目标，能力可跨方向组合；RAG、Coding、Workflow、Browser 是可组合专项。已有项目优先，默认项目候选可替换。新方向资料先核对教程入口，详细章节范围会如实标注。</p>
      </section>
      {pendingRunId && !run && <div className="run-banner" role="status">
        <strong>运行编号已保存，待读回</strong>
        <p className="form-note">运行 {pendingRunId} 暂时无法读取状态。编号已保存；请手动读取状态，不会再次提交。</p>
        <button className="text-button" disabled={busy} onClick={() => act(() => loadRun(pendingRunId))}>手动读取运行状态</button>
      </div>}
      {run && (
        <div className="run-banner" role="status">
          <strong>
            {runNeedsCheck(run)
              ? "运行状态需要核对"
              : draft?.status === "awaiting_approval"
              ? "草案已生成 · 等待确认"
              : draft?.status === "approved"
                ? "路线已发布"
                : draft?.status === "cancelled"
                  ? "草案已取消"
              : run.status === "waiting_user"
                ? "草案等待确认"
              : run.status === "running"
                ? "正在生成"
                : run.status === "queued"
                  ? "等待生成"
                  : run.status === "failed"
                    ? "生成失败"
                    : run.status === "reconciliation_required"
                      ? "运行需要核对，请勿重复调用"
                      : run.status === "succeeded"
                        ? "生成已完成"
                        : "运行已取消"}
          </strong>
          {runNeedsCheck(run) && <p className="form-note">服务返回了当前页面无法安全处理的运行状态或下一步操作。运行编号 {run.run_id} 已保留；请手动刷新状态核对，不会自动重试、重放或启动新运行。</p>}
          {run.status === "failed" && !runNeedsCheck(run) && <p className="form-note">再次生成会创建一条新运行，不会恢复或重派这条失败运行。</p>}
          {run.error && <p>{run.error.message}</p>}
          {!runNeedsCheck(run) && run.next_action === 'wait' && ['queued', 'running'].includes(run.status) && !pendingCancellation && <>
            <p className="form-note">取消后停止后续生成并保留记录；已经发出的请求可能仍返回结果，需要核对。</p>
            <button className="btn quiet" disabled={busy} onClick={() => void cancelGeneration()}>取消生成</button>
          </>}
          {pendingCancellation?.run_id === run.run_id && <>
            <p className="form-note">{pendingCancellation.conflict
              ? '取消未确认，运行版本或状态可能已变化。请刷新运行状态后再决定。'
              : '取消结果尚未确认，运行编号和原请求已保存。请刷新状态核对，或明确重试同一次取消；不会自动提交。'}</p>
            {!pendingCancellation.conflict && <button className="btn quiet" disabled={busy} onClick={() => void cancelGeneration(true)}>重试同一次取消</button>}
          </>}
          <button
            className="text-button"
            disabled={busy}
            onClick={() => act(() => loadRun(run.run_id))}
          >
            刷新运行状态
          </button>
        </div>
      )}
      {run?.progress && <RunProgressPanel progress={run.progress} />}
      {error && (
        <div role="alert" className="error">
          {error}
        </div>
      )}
      <section className="panel" aria-label="运行历史恢复">
        <div className="section-heading">
          <div><h2>运行历史</h2><p className="form-note">只读取当前账号与项目最近的20条规划运行；选择一条后恢复查看，不会重新提交生成。</p></div>
          <button className="btn" disabled={historyBusy || busy} onClick={() => void readServerRuns()}>{historyBusy ? '正在读取…' : '读取服务器上的运行'}</button>
        </div>
        {historyError && <div role="alert" className="error">{historyError}<button className="text-button" disabled={historyBusy} onClick={() => void readServerRuns()}>重新读取运行列表</button></div>}
        {draft?.status === 'awaiting_approval' && <p className="form-note">请先处理当前未确认的草案，再切换到其他运行；未保存的修改会继续保留。</p>}
        {historyOpened && historyRunsScope === runHistoryScope && <div role="region" aria-label="服务器上的运行">
          {historyRuns.length ? <ul>{historyRuns.map(item => {
            const blocked = runBlocksHistorySwitch(item.run_id);
            return <li key={item.run_id} aria-label={item.run_id}>
              <strong>{statusLabel(item.status)}</strong> · 运行编号 <code>{item.run_id}</code>
              {item.result_ref && <p className="form-note">有可读取的草案或路线；选择后查看。</p>}
              {item.error?.message && <p className="form-note">{item.error.message}</p>}
              <button className="btn quiet" disabled={blocked || busy || historyBusy} onClick={() => void selectServerRun(item.run_id)}>
                读取此运行
              </button>
            </li>;
          })}</ul> : <p className="form-note">服务器没有可显示的运行记录。</p>}
          {historyRuns.length === 20 && <p className="form-note">仅显示最近 20 条运行。</p>}
        </div>}
        {pendingHistorySelection && <div role="alert" className="error">
          <p>切换到运行 {pendingHistorySelection} 会丢弃当前未保存的草案编辑。</p>
          <button className="btn" disabled={busy} onClick={() => void selectServerRun(pendingHistorySelection, true)}>丢弃编辑并恢复此运行</button>
          <button className="btn quiet" disabled={busy} onClick={() => setPendingHistorySelection(null)}>保留编辑</button>
        </div>}
      </section>
      {notice && (
        <p className="notice" role="status">
          {notice}
        </p>
      )}
      {conflict && draft && (
        <button
          className="btn"
          disabled={busy}
          onClick={() =>
            act(async () => {
              await loadDraft(draft.draft_id, true);
              setConflict(false);
              setError("");
            })
          }
        >
          重新加载草案
        </button>
      )}
      {draft ? (
        <>
          <div className="section-heading">
            <h2>
              {editable
                ? "检查与调整草案"
                : draft.status === "approved"
                  ? "已确认草案"
                  : "已取消草案"}
            </h2>
            <span className="pill">
              候选版本 {draft.revision} · {stages.length} 个阶段
            </span>
          </div>
          <GoalSpecSnapshot value={draft.goal_spec} />
          {draft.validation_warnings?.map((w) => (
            <p className="form-note" key={w}>
              {w}
            </p>
          ))}
          {draft.change_preview_id && draft.status === "awaiting_approval" && <p className="form-note">这是受保护的全路线调整草案。请在“有限路线调整”中查看完整差异并确认或取消。</p>}
          {stages.map((s, i) => (
            <section className="panel draft-stage" key={s.stage_id}>
              <div className="stage-top">
                <span className="step">{i + 1}</span>
                {editable ? (
                  <input
                    aria-label={`阶段 ${i + 1} 标题`}
                    value={s.title}
                    maxLength={200}
                    onChange={(e) => change(i, "title", e.target.value)}
                  />
                ) : (
                  <h3>{s.title}</h3>
                )}
                {editable && (
                  <div className="order-actions">
                    <button
                      className="btn quiet"
                      disabled={busy || i === 0}
                      onClick={() => move(i, -1)}
                    >
                      上移
                    </button>
                    <button
                      className="btn quiet"
                      disabled={busy || i === stages.length - 1}
                      onClick={() => move(i, 1)}
                    >
                      下移
                    </button>
                  </div>
                )}
              </div>
              {editable ? (
                <textarea
                  aria-label={`阶段 ${i + 1} 目标`}
                  rows={2}
                  value={s.objective}
                  maxLength={1000}
                  onChange={(e) => change(i, "objective", e.target.value)}
                />
              ) : (
                <p>{s.objective}</p>
              )}
              <LearningGuidance guidance={s.learning_guidance} />
              {(draft.extensions ?? []).filter(extension => extension.stage_id === s.stage_id && extension.topic.startsWith('项目学习：')).slice(0, 1).map(extension => (
                <details key={extension.extension_id} aria-label="项目学习安排">
                  <summary>项目案例（可选）：{extension.topic.slice('项目学习：'.length)}</summary>
                  <p style={{whiteSpace:'pre-line'}}>{extension.guidance}</p>
                  <ul>{(extension.concepts ?? []).map(concept => <li key={concept}>{concept}</li>)}</ul>
                  <p className="form-note">确认路线后，可在学习阶段复制项目学习 Prompt 给外部 AI。</p>
                </details>
              ))}
              {(draft.extensions ?? []).filter(extension => extension.stage_id === s.stage_id && (extension.topic.startsWith('资料缺口：') || extension.topic === '持续成果载体与可组合专项')).map(extension => (
                <section key={extension.extension_id} aria-label={extension.topic.startsWith('资料缺口：') ? '资料缺口' : '项目与可组合专项'}>
                  <h3>{extension.topic}</h3>
                  <p style={{whiteSpace:'pre-line'}}>{extension.guidance}</p>
                  <ul>{(extension.concepts ?? []).map(concept => <li key={concept}>{concept}</li>)}</ul>
                </section>
              ))}
              <Resources
                items={(draft.stage_resources ?? []).filter(
                  (r) => r.stage_id === s.stage_id,
                )}
              />
            </section>
          ))}
          {editable && (
            <div className="decision-actions">
              <button
                className="btn"
                disabled={busy || !dirty || conflict}
                onClick={() => act(() => decide("edit"))}
              >
                保存修改
              </button>
              <button
                className="btn primary"
                disabled={busy || dirty || conflict}
                onClick={() => act(() => decide("approve"))}
              >
                确认并发布路线
              </button>
              <button
                className="btn quiet"
                disabled={busy || conflict}
                onClick={() => act(() => decide("cancel"))}
              >
                取消草案
              </button>
              {dirty && <small>请先保存修改</small>}
            </div>
          )}
        </>
      ) : (
        <div className="panel empty">
          <h2>一条路线，从这里展开</h2>
          <p>填写学习目标后，查看完整阶段及资源，再确认成为正式路线。</p>
        </div>
      )}
      <PlanChanges
        key={JSON.stringify([actorKey, project])}
        actorKey={actorKey}
        project={project}
        onPublished={onPublished}
        generationAllowed={!generationLifecycleBlocked}
        changeDraftId={draft?.change_preview_id}
        onGeneratePlanChange={generatePlanChange}
        onDraftDecision={refreshPlanChangeDraft}
        onPreviewPending={setPendingPlanChange}
      />
    </div>
  );
}
