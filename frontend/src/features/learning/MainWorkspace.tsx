import type { StageWorkspace, DTO } from "../../api/types";
import { Resources } from "../../components/Resources";
import { useEffect, useState } from 'react';
import { ResourceDialog } from '../../components/ResourceDialog';
import { stageCompletionLabel } from '../../components/learningNavigation';
import { ResourcePicker } from './ResourcePicker';
import { PreferencePanel } from './PreferencePanel';
import { ResourceChangePanel } from './ResourceChangePanel';
export function KnowledgeNodeView({
  node,
  allNodes,
  selectNode,
}: {
  node: DTO["WorkspaceNodeView"];
  allNodes: DTO["WorkspaceNodeView"][];
  selectNode: (id: string) => void;
}) {
  return (
    <section className="panel node-detail">
      <div className="section-heading">
        <h2>{node.title}</h2>

      </div>
      <h3>学习目标</h3>
      {node.objectives?.length ? (
        <ul>
          {node.objectives.map((o) => (
            <li key={o}>{o}</li>
          ))}
        </ul>
      ) : (
        <p className="muted">该节点暂无补充学习目标。</p>
      )}
      {!!node.child_ids?.length && (
        <>
          <h3>子知识</h3>
          <div className="chips">
            {node.child_ids.map((id) => (
              <button className="btn" key={id} onClick={() => selectNode(id)}
                title={allNodes.find((n) => n.node_id === id)?.objectives?.join("；")}>
                {allNodes.find((n) => n.node_id === id)?.title || "关联子知识"}
              </button>
            ))}
          </div>
        </>
      )}
      <h3>前置知识</h3>
      {node.prerequisite_ids?.length ? (
        <div className="chips">
          {node.prerequisite_ids.map((id) => (
            <button onClick={() => selectNode(id)} className="btn" key={id}>
              {allNodes.find((n) => n.node_id === id)?.title ||
                "关联前置节点（本阶段外）"}
            </button>
          ))}
        </div>
      ) : (
        <p className="muted">该节点未声明前置关系。</p>
      )}
    </section>
  );
}
export function MainWorkspace({
  stage,
  nodeId,
  allNodes,
  selectNode,
  create,
  projectId,
  planId,
  planRevision,
  onPublished,
  practice, summary,
}: {
  stage: StageWorkspace | undefined;
  nodeId: string;
  allNodes: DTO["WorkspaceNodeView"][];
  selectNode: (id: string) => void;
  create: () => void;
  projectId: string;
  planId: string;
  planRevision: number;
  onPublished: () => Promise<void>;
  practice?: () => void; summary?: () => void;
}) {
  const [unitChoice, setUnitChoice] = useState('');
  const [dialog, setDialog] = useState<'mainline' | 'preferences' | 'supplement' | null>(null);
  useEffect(() => setDialog(null), [projectId, planId, stage?.stage.stage_id]);
  const unitId = stage?.units.some(u => u.unit_id === unitChoice) ? unitChoice : stage?.units[0]?.unit_id;
  const node =
    stage?.nodes.find((n) => n.node_id === nodeId) || stage?.nodes[0];
  const validNodeId = stage?.units.find(u=>u.unit_id === unitId)?.node_ids?.includes(node?.node_id || '') ? node?.node_id : undefined;
  const positionKey = `${projectId}:${planId}:${stage?.stage.stage_id}:${unitId}:${validNodeId || ''}`;
  return (
    <div className="content">
      <p className="eyebrow">阶段学习 · {stage ? String(stage.stage.order_index + 1).padStart(2,"0") : ""}</p>
      <div className="page-title-line"><h1>{stage?.stage.title || "阶段学习工作区"}</h1>{stage && <span className="pill stage-completion">{stageCompletionLabel(stage)}</span>}</div>
      <p className="lede">
        {stage?.stage.objective || "确认一条学习路线后，开始当前阶段的学习。"}
      </p>
      {!stage ? (
        <div className="panel empty">
          <p>暂无可学习阶段。</p>
          <button className="btn primary" onClick={create}>
            创建学习目标
          </button>
        </div>
      ) : (
        <>
          <dl className="learning-meta"><div><dt>进入本阶段之前</dt><dd>{[...new Set(stage.nodes.flatMap(n => n.prerequisite_ids || []))].length ? [...new Set(stage.nodes.flatMap(n => n.prerequisite_ids || []))].map(id => {const prerequisite=allNodes.find(n=>n.node_id===id);return prerequisite ? <button key={id} className="prereq-link" onClick={()=>selectNode(id)}>{prerequisite.title}</button> : <span key={id}>关联前置知识暂不可用</span>;}) : '正式计划未声明前置知识。'}</dd></div><div><dt>本阶段实践</dt><dd>{stage.tasks.map(t=>t.title).join('、') || '本阶段尚无正式实践任务。'}</dd></div></dl>
          <div className="section-heading">
            <h2>知识结构</h2>
            <span className="muted">{stage.nodes.length} 个知识节点</span>
          </div>
          <div className="node-tabs">
            {stage.nodes.map((n) => (
              <button
                className={`btn ${node?.node_id === n.node_id ? "selected" : ""}`}
                title={n.title}
                key={n.node_id}
                onClick={() => selectNode(n.node_id)}
              >
                {n.title}
              </button>
            ))}
          </div>
          {node && <KnowledgeNodeView node={node} allNodes={allNodes} selectNode={selectNode} />}
          <div className="section-heading">
            <h2>学习资源</h2>
            <span className="muted">资料来源如实标记</span>
          </div>
          <section className="panel">
            <Resources items={stage.resources.filter((r) => !r.node_ids?.length || r.node_ids.includes(node?.node_id || ""))} />
          </section>
          <div className="resource-actions" aria-label="学习资料操作">
            <button className="btn" onClick={() => setDialog('mainline')}>替换本阶段主线</button>
            <button className="btn" disabled={!unitId} onClick={() => setDialog('preferences')}>资料偏好</button>
            <button className="btn" disabled={!unitId} onClick={() => setDialog('supplement')}>补充本单元资料</button>
          </div>
          {!unitId && <p className="form-note">本阶段尚无学习单元，暂不能设置单元资料偏好或补充资料。</p>}
          <ResourceDialog title="替换本阶段主线" open={dialog === 'mainline'} close={() => setDialog(null)}>
            <ResourceChangePanel key={`mainline:${projectId}:${planId}:${stage.stage.stage_id}`} projectId={projectId}
              planId={planId} revision={planRevision} stageId={stage.stage.stage_id}
              primary={stage.resources.find(resource => resource.role === 'primary')} onPublished={onPublished} />
          </ResourceDialog>
          <ResourceDialog title="资料偏好" open={dialog === 'preferences'} close={() => setDialog(null)}>
            {unitId && <>
              <label>资料所属学习单元<select aria-label="资料所属学习单元" value={unitId} onChange={event => setUnitChoice(event.target.value)}>
                {stage.units.map(unit => <option key={unit.unit_id} value={unit.unit_id}>{unit.title}</option>)}
              </select></label>
              <PreferencePanel key={`prefs:${positionKey}`} projectId={projectId}
                target={{plan_id:planId,stage_id:stage.stage.stage_id,unit_id:unitId,...(validNodeId ? {node_id:validNodeId} : {})}} />
            </>}
          </ResourceDialog>
          <ResourceDialog title="补充本单元资料" open={dialog === 'supplement'} close={() => setDialog(null)}>
            {unitId && <>
              <label>资料所属学习单元<select aria-label="资料所属学习单元" value={unitId} onChange={event => setUnitChoice(event.target.value)}>
                {stage.units.map(unit => <option key={unit.unit_id} value={unit.unit_id}>{unit.title}</option>)}
              </select></label>
              <ResourcePicker key={`resources:${positionKey}`} projectId={projectId} nodeId={validNodeId}
                target={{plan_id:planId,stage_id:stage.stage.stage_id,unit_id:unitId}} />
            </>}
          </ResourceDialog>
          {!!stage.tasks.length && <section className="practice-preview"><p className="eyebrow">把知识用到项目中</p>{stage.tasks.map(t=><article key={t.task_id}><h2>{t.title}</h2><p className="muted">{t.goal}</p><p>验收要求：{t.acceptance?.join('；') || '暂无补充条目'}</p></article>)}{practice && <button className="btn primary" onClick={practice}>查看任务与验收要求 →</button>}</section>}
          {summary && <div className="next-step"><div><strong>整理这个阶段的理解与证据</strong><p className="muted">保留还没验证的部分，便于继续学习。</p></div><button className="btn" onClick={summary}>写阶段总结</button></div>}
          <div className="section-heading">
            <h2>学习单元</h2>
          </div>
          <section className="panel">
            {stage.units.map((u) => (
              <div className="task-row" key={u.unit_id}>
                <span className="task-circle" />
                <strong>{u.title}</strong>
              </div>
            ))}
            <p className="form-note">
              阶段完成由阶段总结及现有实践完成记录自动计算；它不代表知识掌握核验。
            </p>
          </section>
        </>
      )}
    </div>
  );
}
