import { useRef, useState } from 'react';
import type { DTO, StageWorkspace } from '../../api/types';
import { buildProjectStudyPrompt, repositoryRootUrl } from '../../content/projectStudyPrompt';

function guidanceValue(guidance: string, prefix: string) {
  return guidance.split(/\r?\n/).find(line => line.startsWith(prefix))?.slice(prefix.length).trim() || '';
}

export function ProjectStudyCard({ stage, plan, priorNodes, extensions }: {
  stage: StageWorkspace;
  plan: DTO['PlanView'];
  priorNodes: DTO['WorkspaceNodeView'][];
  extensions: DTO['KnowledgeExtensionView'][];
}) {
  const repositories = stage.resources.filter(resource => resource.role === 'case_study' && resource.media_type === 'repo');
  const extension = repositories.length ? extensions.find(item => item.topic.startsWith('项目学习：') && item.links?.some(link => repositoryRootUrl(link))) : undefined;
  const repoUrl = extension?.links?.map(repositoryRootUrl).find(Boolean);
  if (!extension || !repoUrl) return null;
  const title = extension.topic.slice('项目学习：'.length).trim();
  const whyNow = guidanceValue(extension.guidance, '为什么现在：');
  const depth = guidanceValue(extension.guidance, '学习深度：') || plan.goal_spec?.desired_depth || '理解本阶段相关机制';
  const avoid = guidanceValue(extension.guidance, '暂不涉及：');
  const directions: Record<string, string> = { 'agent.application': 'Agent 应用开发', 'ai.fullstack': 'AI 全栈开发', 'cloud.services': '云服务开发与运维', 'python.engineering': 'Python 工程基础' };
  const direction = Object.entries(directions).find(([key]) => plan.source_pack_key?.startsWith(key))?.[1] || plan.goal_spec?.target || plan.goal_snapshot;
  const prompt = buildProjectStudyPrompt({
    repo_url: repoUrl, project_title: title, direction,
    goal_branch: [...new Set([plan.goal_snapshot, plan.goal_spec?.target, ...(plan.goal_spec?.scope || [])].filter(Boolean))].join('；'),
    current_stage: `${stage.stage.title}：${stage.stage.objective}`,
    known_knowledge: [...new Set(priorNodes.map(node => node.title))],
    learning_focus: extension.concepts || [], desired_depth: depth,
    important_questions: extension.thinking_prompts || [], avoid_scope: avoid ? [avoid] : [],
    practice_project_context: stage.tasks.map(task => `${task.title}：${task.goal}；验收：${task.acceptance.join('；')}`).join('\n') || '本阶段尚无正式实践任务，请先向我确认自己的项目与验收目标。',
  });
  return <ProjectStudyContent title={title} repoUrl={repoUrl} whyNow={whyNow} depth={depth} avoid={avoid} extension={extension} prompt={prompt} />;
}

function ProjectStudyContent({ title, repoUrl, whyNow, depth, avoid, extension, prompt }: {
  title: string; repoUrl: string; whyNow: string; depth: string; avoid: string;
  extension: DTO['KnowledgeExtensionView']; prompt: string;
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
    <p className="eyebrow">项目学习</p><h2>{title}</h2>
    <a href={repoUrl} target="_blank" rel="noreferrer">{repoUrl} ↗</a>
    {whyNow && <p>为什么现在：{whyNow}</p>}
    <h3>学习重点</h3><ul>{(extension.concepts || []).map(focus => <li key={focus}>{focus}</li>)}</ul>
    <p>学习深度：{depth}</p>{avoid && <p>暂不涉及：{avoid}</p>}
    {!!extension.thinking_prompts?.length && <><h3>对比与迁移思考</h3><ul>{extension.thinking_prompts.map(question => <li key={question}>{question}</li>)}</ul></>}
    <label>给外部 AI 的源码学习 Prompt<textarea ref={textarea} aria-label="源码学习 Prompt" readOnly rows={12} value={prompt} /></label>
    <p className="form-note">复制前检查学习上下文。复制只写入剪贴板；此页面不会调用 AI 或发送内容。</p>
    <button className="btn primary" onClick={copy}>复制给 AI</button>
    <p role="status" aria-live="polite">{copyState === 'copied' ? '已复制，可粘贴给外部 AI。' : copyState === 'failed' ? '复制失败，已选中文本。请手动复制上方 Prompt。' : ''}</p>
  </section>;
}
