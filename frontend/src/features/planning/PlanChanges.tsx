import { useEffect, useMemo, useRef, useState } from 'react';
import { api, ApiError } from '../../api/client';
import type { DTO } from '../../api/types';

export function PlanChanges({ actorKey, project, onPublished, generationAllowed, changeDraftId, onGeneratePlanChange, onDraftDecision, onPreviewPending }: {
  actorKey: string; project: string; onPublished: () => Promise<void>;
  generationAllowed: boolean;
  changeDraftId?: string | null;
  onGeneratePlanChange: (body: DTO['GeneratedPlanChangeRequest']) => Promise<void>;
  onDraftDecision: (preview: DTO['PlanChangePreviewView']) => Promise<void>;
  onPreviewPending: (pending: boolean) => void;
}) {
  const cacheKey = `studyplan-plan-change:${JSON.stringify([actorKey, project])}`;
  const currentScope = useRef(cacheKey);
  currentScope.current = cacheKey;
  const lease = useMemo(() => ({ key: cacheKey, active: true, busy: false }), [cacheKey]);
  const live = () => lease.active && currentScope.current === lease.key;
  const previewPendingCallback = useRef(onPreviewPending);
  previewPendingCallback.current = onPreviewPending;
  const [context, setContext] = useState<DTO['PlanChangeContext'] | null>(null);
  const [order, setOrder] = useState<string[]>([]);
  const [preview, setPreview] = useState<DTO['PlanChangePreviewView'] | null>(null);
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  const [conflict, setConflict] = useState(false), [acknowledged, setAcknowledged] = useState(false);
  const [notice, setNotice] = useState(''), [opened, setOpened] = useState(false);
  const [noPlan, setNoPlan] = useState(false);
  const [newGoal, setNewGoal] = useState('');
  const pendingPreview = useRef<{ signature: string; body: DTO['PlanChangeRequest'] } | null>(null);
  const pendingConfirm = useRef<{ signature: string; body: DTO['PlanChangeDecisionRequest'] } | null>(null);
  const pendingGenerated = useRef<{ signature: string; body: DTO['GeneratedPlanChangeRequest'] } | null>(null);
  useEffect(() => {
    previewPendingCallback.current(Boolean(preview?.status === 'awaiting_approval' || (!preview && localStorage.getItem(cacheKey))));
    return () => previewPendingCallback.current(false);
  }, [cacheKey, preview]);

  async function act(work: () => Promise<void>) {
    if (!live() || lease.busy) return;
    lease.busy = true;
    setBusy(true);
    setError('');
    try { await work(); }
    catch (failure) {
      if (!live()) return;
      setError(failure instanceof Error ? failure.message : '无法读取路线调整，请核对原预览。');
      if (failure instanceof ApiError && failure.status === 409) setConflict(true);
    } finally {
      lease.busy = false;
      if (live()) setBusy(false);
    }
  }
  async function readContext() {
    try {
      const value = await api.planChangeContext(project);
      if (!live()) return;
      setContext(value);
      setOrder(value.stages.map(stage => stage.stable_key));
      setNewGoal(value.goal || '');
      setNoPlan(false);
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 404) {
        if (live()) { setNoPlan(true); setContext(null); }
      } else throw failure;
    }
  }
  async function readPreview() {
    const id = preview?.proposal_id || localStorage.getItem(cacheKey);
    if (!id) return;
    const value = await api.planChange(project, id);
    if (!live()) return;
    setPreview(value);
    setAcknowledged(false);
    setConflict(false);
    setNotice(value.status === 'approved' ? '新路线已发布。' : value.status === 'cancelled' ? '路线调整已取消。' : '');
  }
  useEffect(() => {
    lease.active = true;
    if (localStorage.getItem(cacheKey)) void act(async () => {
      await readContext();
      if (live()) await readPreview();
    });
    return () => { lease.active = false; };
  }, [lease]);
  useEffect(() => {
    if (opened && !context && !noPlan) void act(readContext);
  }, [opened, context, noPlan]);
  useEffect(() => {
    if (!changeDraftId || !live()) return;
    let cancelled = false;
    const recover = async () => {
      while (lease.busy && live() && !cancelled) await new Promise(resolve => setTimeout(resolve, 25));
      if (!cancelled && live()) void act(async () => {
        const value = await api.planChange(project, changeDraftId);
        if (!live()) return;
        setPreview(value);
        localStorage.setItem(cacheKey, value.proposal_id);
        setAcknowledged(false);
        setConflict(false);
        pendingGenerated.current = null;
      });
    };
    void recover();
    return () => { cancelled = true; };
  }, [changeDraftId, lease]);

  const awaiting = preview?.status === 'awaiting_approval';
  const originalOrder = context?.stages.map(stage => stage.stable_key) || [];
  const changed = JSON.stringify(order) !== JSON.stringify(originalOrder);
  function move(index: number, delta: number) {
    if (!context || busy || awaiting) return;
    const nextIndex = index + delta;
    const stage = context.stages.find(item => item.stable_key === order[index]);
    const neighbour = context.stages.find(item => item.stable_key === order[nextIndex]);
    if (!stage || !neighbour || stage.locked || neighbour.locked) return;
    setOrder(previous => { const next = [...previous]; [next[index], next[nextIndex]] = [next[nextIndex], next[index]]; return next; });
  }
  function createPreview(operation: DTO['PlanChangeRequest']['operation'], stageKey = '') {
    if (!context || !live() || lease.busy || awaiting) return;
    const request = { plan_id: context.plan_id, expected_version: context.revision, operation,
      stage_keys: operation === 'reorder_future_stage' ? order : [], stage_key: stageKey };
    const signature = JSON.stringify(request);
    if (pendingPreview.current?.signature !== signature) pendingPreview.current = {
      signature, body: { ...request, idempotency_key: crypto.randomUUID() },
    };
    const body = pendingPreview.current.body;
    onPreviewPending(true);
    void act(async () => {
      try {
        const value = await api.previewPlanChange(project, body);
        if (!live()) return;
        setPreview(value);
        localStorage.setItem(cacheKey, value.proposal_id);
        setAcknowledged(false);
        setConflict(false);
        setNotice('');
        pendingConfirm.current = null;
      } catch (failure) {
        if (live()) onPreviewPending(awaiting);
        throw failure;
      }
    });
  }
  function generate(operation: DTO['GeneratedPlanChangeRequest']['operation']) {
    if (!context || !generationAllowed || !live() || lease.busy || awaiting) return;
    const target = operation === 'change_goal' ? newGoal.trim() : '';
    if (operation === 'change_goal' && (!target || Array.from(target).length > 2000)) {
      setError('学习目标不能为空，且最多 2000 个字符。');
      return;
    }
    const request = { plan_id: context.plan_id, expected_version: context.revision, operation, goal: target };
    const signature = JSON.stringify(request);
    if (pendingGenerated.current?.signature !== signature) pendingGenerated.current = {
      signature, body: { ...request, idempotency_key: crypto.randomUUID() },
    };
    const body = pendingGenerated.current.body;
    void act(async () => {
      await onGeneratePlanChange(body);
      if (!live()) return;
      pendingGenerated.current = null;
      setNotice('路线调整已进入生成队列，完成后会显示受保护的调整预览。');
    });
  }
  function decide(action: 'confirm' | 'cancel') {
    if (!preview || !awaiting || !live() || lease.busy || (action === 'confirm' && (!acknowledged || conflict))) return;
    const signature = `${action}:${preview.proposal_id}:${preview.preview_hash}`;
    if (pendingConfirm.current?.signature !== signature) pendingConfirm.current = { signature, body: {
      expected_version: preview.base_revision, preview_hash: preview.preview_hash,
      idempotency_key: crypto.randomUUID(), acknowledge_reset: action === 'confirm',
    } };
    const body = pendingConfirm.current.body;
    void act(async () => {
      const value = await (action === 'confirm' ? api.confirmPlanChange : api.cancelPlanChange)(project, preview.proposal_id, body);
      if (!live()) return;
      setPreview(value.preview);
      setAcknowledged(false);
      setConflict(false);
      pendingPreview.current = null;
      setNotice(value.preview.status === 'approved' ? '新路线已发布。' : '路线调整已取消。');
      await onDraftDecision(value.preview);
      if (value.preview.status === 'approved') {
        await onPublished();
        if (live()) await readContext();
      } else if (live()) {
        await readContext();
      }
    });
  }
  const title = (key: string) => preview?.draft.stages?.find(stage => stage.stable_key === key)?.title
    || context?.stages.find(stage => stage.stable_key === key)?.title || '阶段信息暂不可用';

  return <section className="panel" aria-label="有限路线调整">
    <details onToggle={event => setOpened(event.currentTarget.open)}>
      <summary>调整未来路线（有限操作）</summary>
      <p className="form-note">可以调整尚未开始的阶段顺序，或移除正式内容明确标记的可选阶段。已开始阶段及之前阶段保持原位置，最终综合实践保留在末尾。</p>
      <button className="btn" disabled={busy} onClick={() => void act(readContext)}>读取当前路线</button>
      {noPlan && <p className="form-note">当前还没有正式路线，请先生成并确认学习草案。</p>}
      {context && <>
        {!context.stages.some(stage => stage.inclusion === 'optional') &&
          <p className="form-note">当前正式路线没有明确标记为可选的阶段，因此这里不会显示移除选项；必修和推荐内容会保留。</p>}
        <section aria-label="生成未来路线草案">
          <h3>重新生成未来路线</h3>
          <p className="form-note">生成会使用当前配置的模型预算，可能产生费用。重新生成未来阶段的上限为 {context.generation_max_requests} 次模型请求（含修复请求）；改变目标的请求上限未提供。</p>
          <button className="btn" disabled={busy || awaiting || !generationAllowed || !context.regenerate_available || context.generation_max_requests <= 0} onClick={() => generate('regenerate_future_plan')}>重新生成未来阶段</button>
          {!context.regenerate_available && <p className="form-note">当前路线没有可重新生成的未来阶段。</p>}
          <label>新的学习目标<textarea aria-label="新的学习目标" rows={2} maxLength={2000} value={newGoal} onChange={event => setNewGoal(event.target.value)} /></label>
          <button className="btn" disabled={busy || awaiting || !generationAllowed || !newGoal.trim() || newGoal.trim() === context.goal} onClick={() => generate('change_goal')}>生成目标调整草案</button>
        </section>
        <ol aria-label="待预览阶段顺序">{order.map((key, index) => {
          const stage = context.stages.find(item => item.stable_key === key)!;
          const previous = context.stages.find(item => item.stable_key === order[index - 1]);
          const next = context.stages.find(item => item.stable_key === order[index + 1]);
          const inclusionLabel = stage.inclusion === 'optional' ? '可选' : stage.inclusion === 'recommended' ? '推荐' : '必修';
          return <li key={key}>
            <strong>{stage.title}</strong> {stage.locked ? '· 位置固定（学习边界或最终综合实践）' : `· ${inclusionLabel}`}
            <div className="chips">
              <button className="btn quiet" aria-label={`上移 ${stage.title}`} disabled={busy || awaiting || stage.locked || !previous || previous.locked} onClick={() => move(index, -1)}>上移</button>
              <button className="btn quiet" aria-label={`下移 ${stage.title}`} disabled={busy || awaiting || stage.locked || !next || next.locked} onClick={() => move(index, 1)}>下移</button>
              {!stage.locked && stage.inclusion === 'optional' && <button className="btn quiet" aria-label={`预览移除 ${stage.title}`} disabled={busy || awaiting} onClick={() => createPreview('remove_optional_topic', key)}>预览移除</button>}
            </div>
          </li>;
        })}</ol>
        <button className="btn" disabled={busy || awaiting || !changed} onClick={() => createPreview('reorder_future_stage')}>预览阶段顺序</button>
      </>}
      {(preview || localStorage.getItem(cacheKey)) && <button className="btn" disabled={busy} onClick={() => void act(readPreview)}>读取调整预览</button>}
      {error && <p className="error" role="alert">{error}</p>}
      {notice && <p className="notice" role="status">{notice}</p>}
      {preview && <section aria-label="路线调整预览">
        {(preview.operation === 'change_goal' || preview.operation === 'regenerate_future_plan') ? <>
          <h3>目标调整</h3>
          <p><strong>调整前目标：</strong>{preview.before_goal}</p>
          <p><strong>调整后目标：</strong>{preview.after_goal}</p>
          <h3>调整前的完整阶段内容</h3>
          {preview.before_stages?.length ? <ol>{preview.before_stages.map(stage => <li key={stage.stage_id}>
            <strong>{stage.title}</strong><p>{stage.objective}</p>
            {stage.learning_guidance && <details><summary>学习指导</summary>
              <p>{stage.learning_guidance.why_now}</p><p>{stage.learning_guidance.previous_relation}</p>
              <p>本次重点：{stage.learning_guidance.learning_focus.join('；') || '未单独列出'}</p>
              <p>实践增量：{stage.learning_guidance.practice_delta.increment.join('；') || '未单独列出'}</p>
            </details>}
          </li>)}</ol> : <p className="form-note">服务未提供调整前阶段的完整目标文本，以下保留阶段键仅用于定位。</p>}
          {!preview.before_stages?.length && <ol>{preview.before_stage_keys.map(key => <li key={key}>{title(key)}</li>)}</ol>}
          <h3>调整后的完整阶段内容</h3>
          <ol>{(preview.draft.stages ?? []).map(stage => {
            const retained = preview.retained_stage_keys?.includes(stage.stable_key) ?? false;
            return <li key={stage.stage_id}>
              <strong>{retained ? '保留的前置阶段' : '重新生成的未来阶段'} · {stage.title}</strong>
              <p>{stage.objective}</p>
              {stage.learning_guidance && <details><summary>学习指导</summary>
                <p>{stage.learning_guidance.why_now}</p><p>{stage.learning_guidance.previous_relation}</p>
                <p>本次重点：{stage.learning_guidance.learning_focus.join('；') || '未单独列出'}</p>
                {!!stage.learning_guidance.comparison_focus.length && <p>对比问题：{stage.learning_guidance.comparison_focus.join('；')}</p>}
                <p>实践增量：{stage.learning_guidance.practice_delta.increment.join('；') || '未单独列出'}</p>
              </details>}
            </li>;
          })}</ol>
        </> : <>
          <h3>调整前</h3><ol>{preview.before_stage_keys.map(key => <li key={key}>{title(key)}</li>)}</ol>
          <h3>调整后</h3><ol>{preview.after_stage_keys.map(key => <li key={key}>{title(key)}</li>)}</ol>
        </>}
        {preview.warnings.map((warning, index) => <p className="form-note" key={index}>{warning}</p>)}
        <p>旧路线与历史总结、Prompt、成果、证据继续保留；新版学习记录不自动继承旧阶段的完成状态。</p>
        {awaiting && <>
          <label><input type="checkbox" checked={acknowledged} onChange={event => setAcknowledged(event.target.checked)} disabled={busy || conflict} />我已理解新版学习进度会重置</label>
          <div className="chips">
            <button className="btn primary" disabled={busy || conflict || !acknowledged} onClick={() => decide('confirm')}>确认发布新路线</button>
            <button className="btn quiet" disabled={busy || conflict} onClick={() => decide('cancel')}>取消路线调整</button>
          </div>
        </>}
      </section>}
    </details>
  </section>;
}
