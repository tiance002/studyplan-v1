import { useRef, useState } from 'react';
import type { DTO, StageWorkspace } from '../../api/types';
import { buildProjectStudyPrompt, projectStudyGroups } from '../../content/projectStudyPrompt';

function guidanceValue(guidance: string, prefix: string) {
  return guidance.split(/\r?\n/).find(line => line.startsWith(prefix))?.slice(prefix.length).trim() || '';
}

export function ProjectStudyCard({ stage, plan, priorNodes, extensions }: {
  stage: StageWorkspace;
  plan: DTO['PlanView'];
  priorNodes: DTO['WorkspaceNodeView'][];
  extensions: DTO['KnowledgeExtensionView'][];
}) {
  const groups = projectStudyGroups(stage.stage.stage_id, stage.resources, extensions);
  return <>{groups.map(group => <ProjectStudyCandidate key={group.key} stage={stage} plan={plan}
    priorNodes={priorNodes} title={group.title} repoUrl={group.repoUrl}
    pending={group.referenceState === 'pending'} source={group.source} bindingWarnings={group.bindingWarnings} extension={group.extension} />)}</>;
}

function ProjectStudyCandidate({ stage, plan, priorNodes, title, repoUrl, pending, source, bindingWarnings, extension }: {
  stage: StageWorkspace; plan: DTO['PlanView']; priorNodes: DTO['WorkspaceNodeView'][];
  title: string; repoUrl?: string; pending: boolean; extension: DTO['KnowledgeExtensionView'];
  source?: DTO['StageResourceAssignmentView']; bindingWarnings: string[];
}) {
  const whyNow = guidanceValue(extension.guidance, '为什么现在：');
  const depth = guidanceValue(extension.guidance, '学习深度：') || plan.goal_spec?.desired_depth || '理解本阶段相关机制';
  const avoid = guidanceValue(extension.guidance, '暂不涉及：');
  const mode = extension.guidance.match(/whole_core|whole_system|targeted_deep_dive/)?.[0] || '';
  const modeLabels: Record<string, string> = { whole_core: '核心整体认识', whole_system: '系统整体学习', targeted_deep_dive: '目标切片深入学习' };
  const directions: Record<string, string> = { 'agent.application': 'Agent 应用开发', 'ai.fullstack': 'AI 全栈开发', 'cloud.services': '云服务开发与运维', 'python.engineering': 'Python 工程基础' };
  const direction = Object.entries(directions).find(([key]) => plan.source_pack_key?.startsWith(key))?.[1] || plan.goal_spec?.target || plan.goal_snapshot;
  const prompt = buildProjectStudyPrompt({
    repo_url: repoUrl || '待选择可核验的参考项目，请先确认候选与允许检查的本地目录。', project_title: title, direction,
    goal_branch: [...new Set([plan.goal_snapshot, plan.goal_spec?.target, ...(plan.goal_spec?.scope || [])].filter(Boolean))].join('；'),
    current_stage: `${stage.stage.title}：${stage.stage.objective}`,
    known_knowledge: [...new Set(priorNodes.map(node => node.title))],
    learning_focus: extension.concepts || [], desired_depth: depth,
    important_questions: extension.thinking_prompts || [], avoid_scope: avoid ? [avoid] : [],
    study_mode: mode ? `${mode}（${modeLabels[mode]}）` : '请按下方完整指导确认学习方式', study_guidance: extension.guidance,
    practice_project_context: stage.tasks.map(task => `${task.title}：${task.goal}；验收：${task.acceptance.join('；')}`).join('\n') || '本阶段尚无正式实践任务，请先向我确认自己的项目与验收目标。',
  });
  return <ProjectStudyContent title={title} repoUrl={repoUrl} pending={pending} source={source} bindingWarnings={bindingWarnings} whyNow={whyNow} depth={depth} avoid={avoid}
    mode={mode ? `${modeLabels[mode]}（${mode}）` : ''} extension={extension} prompt={prompt} />;
}

function ProjectStudyContent({ title, repoUrl, pending, source, bindingWarnings, whyNow, depth, avoid, mode, extension, prompt }: {
  title: string; repoUrl?: string; pending: boolean; whyNow: string; depth: string; avoid: string; mode: string;
  extension: DTO['KnowledgeExtensionView']; prompt: string;
  source?: DTO['StageResourceAssignmentView']; bindingWarnings: string[];
}) {
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'failed'>('idle');
  const textarea = useRef<HTMLTextAreaElement>(null);
  async function copy() {
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(prompt);
      setCopyState('copied');
    } catch {
      setCopyState('failed');
      textarea.current?.focus();
      textarea.current?.select();
    }
  }
  return <section className="panel project-study-card" aria-label="项目源码学习">
    <p className="eyebrow">项目案例（可选）</p><h2>{title}</h2>
    <p className="form-note">可由自己的真实项目替换；无需选择或安装此项目案例。</p>
    {pending && <p className="form-note">参考项目待确认：请确认可核验仓库与本阶段学习重点；当前学习目标保留在下方。合适的成熟用户项目也可作为候选。</p>}
    {bindingWarnings.map((warning, index) => <p className="form-note" key={index}>{warning}</p>)}
    {source && <p className="form-note">来源记录：{source.title} · 版本 {source.source_version || '待核对'} · {({reviewed: '已审核范围', legacy_index: '目录级来源记录', metadata_only: '仅核对元数据'} as Record<string,string>)[source.verification_status] || source.verification_status || '核对状态未提供'}。来源标记不代表已运行或已掌握。</p>}
    {source?.warnings?.map((warning, index) => <p className="form-note" key={`source-warning:${index}`}>{warning}</p>)}
    {repoUrl && <a href={repoUrl} target="_blank" rel="noreferrer">{repoUrl} ↗</a>}
    {mode && <p>学习方式：{mode}</p>}
    {whyNow && <p>为什么现在：{whyNow}</p>}
    <h3>学习重点</h3><ul>{(extension.concepts || []).map(focus => <li key={focus}>{focus}</li>)}</ul>
    <p>学习深度：{depth}</p>{avoid && <p>暂不涉及：{avoid}</p>}
    {!!extension.thinking_prompts?.length && <><h3>对比与迁移思考</h3><ul>{extension.thinking_prompts.map(question => <li key={question}>{question}</li>)}</ul></>}
    {extension.guidance ? <><h3>完整学习指导</h3><p style={{ whiteSpace: 'pre-wrap' }}>{extension.guidance}</p></> : <p className="form-note">此来源尚未提供已绑定的学习指导。</p>}
    {!!extension.search_hints?.length && <p>下一步候选核查：{extension.search_hints.join('；')}</p>}
    <label>给外部 AI 的源码学习 Prompt<textarea ref={textarea} aria-label="源码学习 Prompt" readOnly rows={12} value={prompt} /></label>
    <p className="form-note">复制前检查学习上下文。复制只写入剪贴板；此页面不会调用 AI 或发送内容。</p>
    <button className="btn primary" onClick={copy}>复制给 AI</button>
    <p role="status" aria-live="polite">{copyState === 'copied' ? '已复制，可粘贴给外部 AI。' : copyState === 'failed' ? '复制失败，已选中文本。请手动复制上方 Prompt。' : ''}</p>
  </section>;
}
