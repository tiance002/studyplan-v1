import { useState } from 'react';
import type { DTO, Page } from '../api/types';
import { toggleStage, stageCompletionLabel, stageTotals } from './learningNavigation';

export function LearningPlanSidebar({
  workspace, stageId, nodeId, selectStage, selectNode, selectTask, navigate,
}: {
  workspace: DTO['LearningWorkspaceView'] | null;
  stageId: string;
  nodeId: string;
  selectStage: (id: string) => void;
  selectNode: (id: string) => void;
  selectTask?: (stageId: string, taskId: string) => void;
  navigate: (page: Page) => void;
}) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const totals = stageTotals(workspace);

  function openStagePage(id: string, page: Page) {
    selectStage(id);
    navigate(page);
  }

  return (
    <aside className="plan-sidebar" aria-label="学习计划栏">
      <div className="course-top">
        <p className="eyebrow">当前学习计划</p>
        <h2>{workspace?.plan.goal_snapshot || '你的学习路线'}</h2>
        <p className="muted">
          {workspace
            ? `版本 ${workspace.plan.revision} · ${totals.completed}/${totals.total} 阶段完成`
            : '确认计划后，在这里浏览学习结构。'}
        </p>
        {workspace && (
          <progress className="plan-meter" aria-label="阶段完成进度"
            value={totals.completed} max={totals.total || 1} />
        )}
      </div>
      <div className="course-list">
        <div className="course-label">学习阶段 · 点击展开</div>
        {workspace?.stages.map(stageWorkspace => {
          const {stage, nodes, tasks} = stageWorkspace;
          return (
            <section className="stage-group" key={stage.stage_id}>
              <button
                className={`stage-trigger ${stage.stage_id === stageId ? 'current' : ''}`}
                aria-expanded={expanded === stage.stage_id}
                aria-controls={`stage-children-${stage.stage_id}`}
                aria-current={stage.stage_id === stageId ? 'step' : undefined}
                onClick={() => {
                  setExpanded(toggleStage(expanded, stage.stage_id));
                  selectStage(stage.stage_id);
                }}
              >
                <span className="stage-number">{String(stage.order_index + 1).padStart(2, '0')}</span>
                <span className="stage-title">
                  {stage.title}
                  <small>{stageCompletionLabel(stageWorkspace)}</small>
                </span>
                <span className="chevron" aria-hidden="true" />
              </button>
              <div className="stage-children" id={`stage-children-${stage.stage_id}`}
                hidden={expanded !== stage.stage_id}>
                <div className="child-caption">知识节点</div>
                {nodes.map(node => (
                  <button
                    className={`node-button ${stageId === stage.stage_id && nodeId === node.node_id ? 'selected' : ''}`}
                    key={node.node_id}
                    aria-pressed={stageId === stage.stage_id && nodeId === node.node_id}
                    onClick={() => selectNode(node.node_id)}
                  >
                    <span>{node.title}</span>
                  </button>
                ))}
                {!nodes.length && <p className="side-empty">暂无知识节点</p>}
                <div className="child-caption">阶段成果</div>
                <button className="stage-practice" onClick={() => openStagePage(stage.stage_id, 'summary')}>
                  整理阶段总结 →
                </button>
                {tasks.map(task => (
                  <button className="stage-practice" key={task.task_id}
                    onClick={() => selectTask ? selectTask(stage.stage_id, task.task_id) : openStagePage(stage.stage_id, 'practice')}>
                    {task.title} →
                  </button>
                ))}
              </div>
            </section>
          );
        }) || (
          <button className="side-item" onClick={() => navigate('planning')}>创建第一条学习计划</button>
        )}
      </div>
      <div className="side-foot">阶段完成由阶段总结及实践完成记录自动计算。</div>
    </aside>
  );
}
