import type { StageWorkspace, DTO } from "../../api/types";
import { Resources } from "../../components/Resources";
import { useEffect, useState } from 'react';
import { ResourceDialog } from '../../components/ResourceDialog';
import { stageCompletionLabel } from '../../components/learningNavigation';
import { ResourcePicker } from './ResourcePicker';
import { PreferencePanel } from './PreferencePanel';
import { ResourceChangePanel } from './ResourceChangePanel';
import { LearningGuidance } from './LearningGuidance';
import { ProjectStudyCard } from './ProjectStudyCard';
import './MainWorkspace.css';

export function LearningUnits({ units, nodes, selectNode }: {
  units: StageWorkspace['units'];
  nodes: StageWorkspace['nodes'];
  selectNode: (nodeId: string, unitId: string) => void;
}) {
  return <section className="panel learning-units" aria-label="本阶段学习单元">
    <div className="section-heading"><h2>本阶段学习单元</h2><span className="muted">按计划顺序学习</span></div>
    {units.length ? <ol className="learning-unit-list">{units.map((unit, index) => (
      <li key={unit.unit_id} className="learning-unit" data-unit-id={unit.unit_id}>
        <p className="eyebrow">学习单元 {String(index + 1).padStart(2, '0')}</p>
        <h3>{unit.title}</h3>
        <h4>单元学习目标</h4>
        {unit.objectives?.length ? <ul>{unit.objectives.map((objective, objectiveIndex) => <li key={objectiveIndex}>{objective}</li>)}</ul>
          : <p className="muted">计划未提供补充单元目标，可参照关联知识的目标。</p>}
        <h4>关联知识</h4>
        <div className="chips">{unit.node_ids?.length ? unit.node_ids.map(id => {
          const linkedNode = nodes.find(node => node.node_id === id);
          return linkedNode ? <button className="btn" key={id} onClick={() => selectNode(id, unit.unit_id)}>{linkedNode.title}</button>
            : <span className="muted" key={id}>关联知识暂不可用</span>;
        }) : <span className="muted">计划未提供知识关联。</span>}</div>
      </li>
    ))}</ol> : <p className="muted">本阶段尚无学习单元。</p>}
    <p className="form-note">多个单元可以学习同一受控知识。阶段完成由阶段总结及现有实践完成记录自动计算；它不代表知识掌握核验。</p>
  </section>;
}

function stageLearningRole(stage: StageWorkspace, plan?: DTO['PlanView']) {
  // Only use explicit saved presentation facts; do not classify a repository by size or popularity.
  if (/成熟工程[：:]/.test(stage.stage.title)) return '成熟工程 · 目标切片';
  if (/专项教程/.test(stage.stage.title)) return '专项教程';
  const guidance = [...(plan?.extensions || [])
    .filter(extension => extension.stage_id === stage.stage.stage_id && extension.topic.startsWith('项目学习：'))
    .map(extension => extension.guidance || '')].join('\n');
  if (/whole_core|whole_system/.test(guidance)) return '小型源码 · 核心整体学习';
  return '';
}
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
  actorKey,
  planId,
  planRevision,
  onPublished,
  practice, summary, startPractice,
  plan, introducedNodeIds = [],
}: {
  stage: StageWorkspace | undefined;
  nodeId: string;
  allNodes: DTO["WorkspaceNodeView"][];
  selectNode: (id: string) => void;
  create: () => void;
  projectId: string;
  actorKey: string;
  planId: string;
  planRevision: number;
  onPublished: () => Promise<void>;
  practice?: () => void; summary?: () => void; startPractice?: (taskId:string)=>void;
  plan?: DTO['PlanView'];
  introducedNodeIds?: string[];
}) {
  const [unitChoice, setUnitChoice] = useState('');
  const [dialog, setDialog] = useState<'mainline' | 'preferences' | 'supplement' | null>(null);
  useEffect(() => setDialog(null), [projectId, planId, stage?.stage.stage_id]);
  const unitId = stage?.units.some(u => u.unit_id === unitChoice) ? unitChoice : stage?.units[0]?.unit_id;
  const node =
    stage?.nodes.find((n) => n.node_id === nodeId) || stage?.nodes[0];
  const validNodeId = stage?.units.find(u=>u.unit_id === unitId)?.node_ids?.includes(node?.node_id || '') ? node?.node_id : undefined;
  const positionKey = `${projectId}:${planId}:${stage?.stage.stage_id}:${unitId}:${validNodeId || ''}`;
  const stageNodeIds = new Set(stage?.nodes.map(n => n.node_id));
  const entryPrerequisites = [...new Set(stage?.nodes.flatMap(n => n.prerequisite_ids || []))]
    .filter(id => !stageNodeIds.has(id));
  return (
    <div className="content">
      <p className="eyebrow">阶段学习 · {stage ? String(stage.stage.order_index + 1).padStart(2,"0") : ""}</p>
      <div className="page-title-line"><h1>{stage?.stage.title || "阶段学习工作区"}</h1>{stage && <span className="pill stage-completion">{stageCompletionLabel(stage)}</span>}</div>
      <p className="lede">
        {stage?.stage.objective || "确认一条学习路线后，开始当前阶段的学习。"}
      </p>
      {stage && stageLearningRole(stage, plan) && <p className="form-note" aria-label="阶段学习类型">{stageLearningRole(stage, plan)}</p>}
      {!stage ? (
        <div className="panel empty">
          <p>暂无可学习阶段。</p>
          <button className="btn primary" onClick={create}>
            创建学习目标
          </button>
        </div>
      ) : (
        <>
          <dl className="learning-meta"><div><dt>进入本阶段之前</dt><dd>{entryPrerequisites.length ? entryPrerequisites.map(id => {const prerequisite=allNodes.find(n=>n.node_id===id);return prerequisite ? <button key={id} className="prereq-link" onClick={()=>selectNode(id)}>{prerequisite.title}</button> : <span key={id}>关联前置知识暂不可用</span>;}) : '正式计划未声明前置知识。'}</dd></div><div><dt>本阶段实践</dt><dd>{stage.tasks.map(t=>t.title).join('、') || '本阶段尚无正式实践任务。'}</dd></div></dl>
          <LearningUnits units={stage.units} nodes={stage.nodes} selectNode={(id, selectedUnitId) => {setUnitChoice(selectedUnitId); selectNode(id);}} />
          <LearningGuidance key={`${projectId}:${planId}:${planRevision}:${stage.stage.stage_id}`} guidance={stage.stage.learning_guidance} />
          {plan && <ProjectStudyCard key={`project-study:${projectId}:${planId}:${planRevision}:${stage.stage.stage_id}`} stage={stage} plan={plan}
            priorNodes={allNodes.filter(node => introducedNodeIds.includes(node.node_id))}
            extensions={(plan.extensions || []).filter(extension => extension.stage_id === stage.stage.stage_id)} />}
          {(plan?.extensions || []).filter(extension => extension.stage_id === stage.stage.stage_id && !extension.topic.startsWith('项目学习：')).map(extension => (
            <section className="panel" key={extension.extension_id} aria-label="对比与思考提示">
              <h2>{extension.topic}</h2>
              {!!extension.concepts?.length && <ul>{extension.concepts.map(concept => <li key={concept}>{concept}</li>)}</ul>}
              {extension.guidance && <p style={{ whiteSpace: 'pre-line' }}>{extension.guidance}</p>}
              {!!extension.thinking_prompts?.length && <ul>{extension.thinking_prompts.map(question => <li key={question}>{question}</li>)}</ul>}
            </section>
          ))}
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
              <ResourcePicker key={`resources:${positionKey}`} actorKey={actorKey} projectId={projectId} nodeId={validNodeId}
                moduleTitles={Object.fromEntries(stage.nodes.map(node => [node.stable_key,node.title]))}
                topic={stage.nodes.find(node => node.node_id === validNodeId)?.title || stage.stage.title}
                target={{plan_id:planId,stage_id:stage.stage.stage_id,unit_id:unitId,...(validNodeId ? {node_id:validNodeId} : {})}} />
            </>}
          </ResourceDialog>
          {!!stage.tasks.length && <section className="practice-preview"><p className="eyebrow">把知识用到项目中</p>{stage.tasks.map(t=><article key={t.task_id}><h2>{t.title}</h2><p className="muted">{t.goal}</p><p>验收要求：{t.acceptance?.join('；') || '暂无补充条目'}</p>{startPractice&&<button className="btn" onClick={()=>startPractice(t.task_id)}>开始实践</button>}</article>)}{practice && <button className="btn primary" onClick={practice}>查看任务与验收要求 →</button>}</section>}
          {summary && <div className="next-step"><div><strong>整理这个阶段的理解与证据</strong><p className="muted">保留还没验证的部分，便于继续学习。</p></div><button className="btn" onClick={summary}>开始总结</button></div>}
        </>
      )}
    </div>
  );
}
