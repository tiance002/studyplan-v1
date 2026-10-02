import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../../api/client";
import type { DTO } from "../../api/types";
import { Resources } from "../../components/Resources";

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

export function PlanningPage({
  project,
  onPublished,
  fake,
}: {
  project: string;
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
  const generating = useRef(false);
  const loadedDraft = useRef<string | null>(null);
  const [pollAttempt, setPollAttempt] = useState(0);
  const [acceptedRun, setAcceptedRun] = useState(false);
  const generationBlocked = busy || acceptedRun || !goal.trim() || fake === null ||
    draft?.status === "awaiting_approval" ||
    run?.status === "queued" || run?.status === "running" ||
    run?.status === "reconciliation_required";
  async function loadDraft(id: string, force = false) {
    // Status polling must never replace the user's editable snapshot or its base version.
    if (!force && loadedDraft.current === id) return;
    const d = await api.draft(project, id);
    const current = await api.current(project);
    loadedDraft.current = id;
    setDraft(d);
    setStages(d.stages ?? []);
    setBaseVersion(current?.revision ?? 0);
  }
  async function loadRun(id: string) {
    const r = await api.run(project, id);
    setRun(r);
    setAcceptedRun(["queued", "running", "reconciliation_required"].includes(r.status));
    if (r.result_ref && (r.next_action === "review_draft" || r.status === "succeeded")) {
      try {
        await loadDraft(r.result_ref);
      } catch (e) {
        // Historical successful Runs reference a plan. Resolve it by API identity,
        // without assuming the opaque result_ref has a particular prefix.
        if (!(e instanceof ApiError && e.status === 404 &&
            (await api.current(project))?.plan_id === r.result_ref)) throw e;
      }
    }
  }
  useEffect(() => {
    const id = localStorage.getItem(`studyplan-run:${project}`);
    if (id) loadRun(id).catch((e) => setError(e.message));
  }, [project]);
  useEffect(() => {
    if (!run || !["queued", "running"].includes(run.status)) return;
    const timer = setTimeout(
      () => loadRun(run.run_id).catch((e) => setError(e.message))
        .finally(() => setPollAttempt(n => n + 1)),
      document.hidden ? 30000 : Math.min(10000, 1500 * 1.5 ** pollAttempt),
    );
    return () => clearTimeout(timer);
  }, [run, pollAttempt]);
  async function act(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const dirty =
      !!draft && JSON.stringify(stages) !== JSON.stringify(draft.stages ?? []),
    editable = draft?.status === "awaiting_approval";
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
              localStorage.setItem(`studyplan-run:${project}`, result.run_id);
              // A failed first GET is shown as an error, never another POST.
              setAcceptedRun(true);
              setPollAttempt(0);
              loadedDraft.current = null;
              setDraft(null);
              setConflict(false);
              setNotice("");
              await loadRun(result.run_id);
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
        <p className="form-note">支持 Agent 应用开发与 Python 工程入门；其他方向生成通用结构，仅提供资料搜索建议。</p>
      </section>
      {run && (
        <div className="run-banner" role="status">
          <strong>
            {draft?.status === "awaiting_approval"
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
          {run.error && <p>{run.error.message}</p>}
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
    </div>
  );
}
