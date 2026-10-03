/// <reference types="vite/client" />
import { useState } from 'react';
import type { DTO } from '../../api/types';
import { Resources } from '../../components/Resources';
import {stageCompletionLabel, stageTotals} from '../../components/learningNavigation';
import { agentCurriculum, curriculumSources } from '../../content/agentCurriculum';
import type { CurriculumStage } from '../../content/agentCurriculum';

function Capability({ item }: { item: CurriculumStage }) {
  return (
    <article className="capability-row">
      <h3>{item.title} {item.optional && <span className="pill warm">{item.key === 'rlTraining' ? '可选进阶' : '按目标选修'}</span>}</h3>
      <p>{item.objective}</p>
      <small>先修：{item.prerequisites.map(key => agentCurriculum.find(stage => stage.key === key)?.title).join('、') || '从这里开始'}</small>
      <ul>{item.notes.map(note => <li key={note}>{note}</li>)}</ul>
    </article>
  );
}

function CurriculumRecommendations() {
  const stages = (keys: string[]) => keys.map(key => agentCurriculum.find(stage => stage.key === key)!);
  return (
    <section className="recommendation-view" aria-label="建议能力路线">
      <p className="eyebrow">开发预览 · 静态测试示例</p>
      <h2>从能运行，到能评估与改进</h2>
      <p className="lede">围绕你的主项目选择能力。评测从第一个可运行的 Agent 开始；完整 RL 训练属于可选进阶。当前正式计划和任务验收要求保持原样。</p>
      <p className="form-note">此处仅供开发预览，正式学习路线以已发布 Plan 为准；不代表已阅读或已掌握。</p>
      <section className="curriculum-section"><h2>建立基础与第一个 Agent</h2>
        {stages(['python', 'llm', 'tools', 'minAgent']).map(item => <Capability key={item.key} item={item} />)}
      </section>
      <section className="curriculum-section"><h2>按目标选择能力分支</h2>
        <p className="muted">两条分支都依赖工具调用与最小 Agent，不互为先修。知识应用优先 RAG；调试与自动化优先 Workflow，可按主项目需要组合。</p>
        <div className="capability-branches">{stages(['rag', 'workflow']).map(item => <Capability key={item.key} item={item} />)}</div>
      </section>
      <section className="curriculum-section"><h2>管理上下文，再按目标接入工具</h2>
        {stages(['memory', 'mcp']).map(item => <Capability key={item.key} item={item} />)}
      </section>
      <section className="curriculum-section"><h2>系统评测与奖励基础</h2>
        <Capability item={stages(['eval'])[0]} />
      </section>
      <section className="curriculum-section"><h2>理解 Agentic RL，按条件选择训练</h2>
        {stages(['rlBasics', 'rlTraining']).map(item => <Capability key={item.key} item={item} />)}
      </section>
      <section className="curriculum-section"><h2>评估、优化与交付主项目</h2>
        <p className="muted">高级评估只要求 Eval 基础。你可以直接进入诊断与优化，无需先完成 RL 训练。</p>
        {stages(['advancedEval', 'capstone']).map(item => <Capability key={item.key} item={item} />)}
      </section>
      <h3>参考来源</h3>
      <div className="recommendation-sources">{curriculumSources.map(source => <a href={source.url} key={source.url} target="_blank" rel="noreferrer">{source.title} ↗</a>)}</div>
    </section>
  );
}

export function LearningPath({ workspace, enterStage, create }: {
  workspace: DTO['LearningWorkspaceView'] | null;
  enterStage: (id: string) => void;
  create: () => void;
}) {
  const [view, setView] = useState<'current' | 'recommended'>('current');
  const preview = import.meta.env.DEV && new URLSearchParams(window.location.search).get('previewCurriculum') === '1';
  const totals = stageTotals(workspace);
  return (
    <div className="content">
      <p className="eyebrow">学习路径</p>
      <h1>你的学习路径</h1>
      <p className="lede">查看正式计划中的阶段、资料与任务，按目标继续学习和实践。</p>
      {preview && <div className="path-view-toggle" role="group" aria-label="学习路径视图">
        <button className={`btn ${view === 'current' ? 'selected' : ''}`} aria-pressed={view === 'current'} onClick={() => setView('current')}>当前正式路线</button>
        <button className={`btn ${view === 'recommended' ? 'selected' : ''}`} aria-pressed={view === 'recommended'} onClick={() => setView('recommended')}>课程改进建议</button>
      </div>}
      {preview && view === 'recommended' ? <CurriculumRecommendations /> : workspace ? (
        <>
          <div className="goal-banner">
            <span className="pill">正式路线 · 版本 {workspace.plan.revision}</span>
            <h2>{workspace.plan.goal_snapshot}</h2>
            <p className="muted">{totals.completed}/{totals.total} 个阶段已完成</p>
          </div>
          <div className="timeline">
            {workspace.stages.map(stageWorkspace => {
              const {stage, units, resources} = stageWorkspace;
              return (
                <section className="timeline-stage panel" key={stage.stage_id}>
                  <span className="step">{stage.order_index + 1}</span>
                  <div className="section-heading"><h2>{stage.title}</h2>
                    <button className="btn" onClick={() => enterStage(stage.stage_id)}>进入学习 →</button>
                  </div>
                  <p className="muted">{stage.objective}</p><span className="pill">{stageCompletionLabel(stageWorkspace)}</span>
                  <div className="chips">{units.map(unit => <span className="pill" key={unit.unit_id}>{unit.title}</span>)}</div>
                  <Resources items={resources} />
                </section>
              );
            })}
          </div>
        </>
      ) : (
        <div className="panel empty"><h2>还没有正式路线</h2>
          <p>先创建目标并确认草案，学习路径就会在这里展开。</p>
          <button className="btn primary" onClick={create}>创建学习目标</button>
        </div>
      )}
    </div>
  );
}
