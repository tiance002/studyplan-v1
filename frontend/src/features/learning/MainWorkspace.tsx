import type { StageWorkspace, DTO } from "../../api/types";
import { Resources } from "../../components/Resources";
import { useState } from 'react';
import { ResourcePicker } from './ResourcePicker';
import { ExposurePanel, progressLabels } from './ExposurePanel';
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
        <span className="pill warm">
          {node.source_status === "verified"
            ? "来源已核验"
            : "AI 草稿 · 待核验"}
        </span>
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
            <span title={id} className="pill" key={id}>
              {allNodes.find((n) => n.node_id === id)?.title ||
                "关联前置节点（本阶段外）"}
            </span>
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
}) {
  const [unitChoice, setUnitChoice] = useState('');
  const [localProgress, setLocalProgress] = useState<Record<string, DTO['ExposureView']>>({});
  const unitId = stage?.units.some(u => u.unit_id === unitChoice) ? unitChoice : stage?.units[0]?.unit_id;
  const node =
    stage?.nodes.find((n) => n.node_id === nodeId) || stage?.nodes[0];
  const validNodeId = stage?.units.find(u=>u.unit_id === unitId)?.node_ids?.includes(node?.node_id || '') ? node?.node_id : undefined;
  const positionKey = `${projectId}:${planId}:${stage?.stage.stage_id}:${unitId}:${validNodeId || ''}`;
  return (
    <div className="content">
      <p className="eyebrow">STAGE WORKSPACE</p>
      <h1>{stage?.stage.title || "阶段学习工作区"}</h1>
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
          <div className="goal-banner">
            <span className="pill">本阶段目标</span>
            <p>{stage.stage.objective}</p>
          </div>
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
          <ResourceChangePanel key={`mainline:${projectId}:${planId}:${stage.stage.stage_id}`} projectId={projectId}
            planId={planId} revision={planRevision} stageId={stage.stage.stage_id}
            primary={stage.resources.find(r => r.role === 'primary')} onPublished={onPublished} />
          {unitId && stage && <>
            <label>资料所属学习单元<select aria-label="资料所属学习单元" value={unitId} onChange={e => setUnitChoice(e.target.value)}>
              {stage.units.map(u => <option key={u.unit_id} value={u.unit_id}>{u.title}</option>)}
            </select></label>
            <ExposurePanel key={`progress:${positionKey}`} projectId={projectId}
              target={{plan_id:planId,stage_id:stage.stage.stage_id,unit_id:unitId}} onChange={value=>setLocalProgress(old=>({...old,[`${value.plan_id}:${value.stage_id}:${value.unit_id}`]:value}))} />
            <PreferencePanel key={`prefs:${positionKey}`} projectId={projectId}
              target={{plan_id:planId,stage_id:stage.stage.stage_id,unit_id:unitId,...(validNodeId ? {node_id:validNodeId} : {})}} />
            <ResourcePicker key={`resources:${positionKey}`} projectId={projectId} nodeId={validNodeId}
              target={{plan_id: planId, stage_id: stage.stage.stage_id, unit_id: unitId}} />
          </>}
          <div className="section-heading">
            <h2>学习单元</h2>
          </div>
          <section className="panel">
            {stage.units.map((u) => (
              <div className="task-row" key={u.unit_id}>
                <span className="task-circle" />
                <strong>{u.title}</strong>
                <small>
                  {localProgress[`${planId}:${stage.stage.stage_id}:${u.unit_id}`]
                    ? progressLabels[localProgress[`${planId}:${stage.stage.stage_id}:${u.unit_id}`].status]
                    : !u.progress_recorded ? "学习单元" : progressLabels[u.progress]}
                </small>
              </div>
            ))}
            <p className="form-note">
              显示当前出现位置的自述进度；跳过不等于完成，进度不代表知识掌握核验。
            </p>
          </section>
        </>
      )}
    </div>
  );
}
