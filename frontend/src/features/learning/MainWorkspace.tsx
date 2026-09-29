import type { StageWorkspace, DTO } from "../../api/types";
import { Resources } from "../../components/Resources";
export function KnowledgeNodeView({
  node,
  allNodes,
}: {
  node: DTO["WorkspaceNodeView"];
  allNodes: DTO["WorkspaceNodeView"][];
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
}: {
  stage: StageWorkspace | undefined;
  nodeId: string;
  allNodes: DTO["WorkspaceNodeView"][];
  selectNode: (id: string) => void;
  create: () => void;
}) {
  const node =
    stage?.nodes.find((n) => n.node_id === nodeId) || stage?.nodes[0];
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
          {node && <KnowledgeNodeView node={node} allNodes={allNodes} />}
          <div className="section-heading">
            <h2>学习资源</h2>
            <span className="muted">资料来源如实标记</span>
          </div>
          <section className="panel">
            <Resources items={stage.resources} />
          </section>
          <div className="section-heading">
            <h2>学习单元</h2>
          </div>
          <section className="panel">
            {stage.units.map((u) => (
              <div className="task-row" key={u.unit_id}>
                <span className="task-circle" />
                <strong>{u.title}</strong>
                <small>
                  {u.progress === "completed"
                    ? "已完成"
                    : u.progress === "in_progress"
                      ? "学习中"
                      : "未开始"}
                </small>
              </div>
            ))}
            <p className="form-note">
              当前显示已记录的学习进度。进度记录和总结评审将在后续开放。
            </p>
          </section>
        </>
      )}
    </div>
  );
}
