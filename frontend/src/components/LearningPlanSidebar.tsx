import type { DTO, StageWorkspace, Page } from "../api/types";
export function LearningPlanSidebar({
  workspace,
  stageId,
  nodeId,
  selectStage,
  selectNode,
  navigate,
}: {
  workspace: DTO["LearningWorkspaceView"] | null;
  stageId: string;
  nodeId: string;
  selectStage: (id: string) => void;
  selectNode: (id: string) => void;
  navigate: (p: Page) => void;
}) {
  const stage = workspace?.stages.find((s) => s.stage.stage_id === stageId);
  const row = (s: StageWorkspace) => (
    <button
      className={`side-item ${s.stage.stage_id === stageId ? "active" : ""}`}
      key={s.stage.stage_id}
      title={s.stage.title}
      onClick={() => selectStage(s.stage.stage_id)}
    >
      <span className="side-title">
        {s.stage.order_index + 1}. {s.stage.title}
      </span>
      <small>阶段</small>
    </button>
  );
  return (
    <aside className="plan-sidebar" aria-label="学习计划栏">
      <div className="course-top">
        <p className="eyebrow">LEARNING PLAN</p>
        <h2 title={workspace?.plan.goal_snapshot}>
          {workspace?.plan.goal_snapshot || "你的学习路线"}
        </h2>
        <p className="muted">
          {workspace
            ? `版本 ${workspace.plan.revision} · ${workspace.completed_units}/${workspace.total_units} 单元完成`
            : "确认计划后，在这里浏览学习结构。"}
        </p>
      </div>
      <div className="course-list">
        <div className="course-label">学习阶段</div>
        {workspace?.stages.map(row) || (
          <button className="side-item" onClick={() => navigate("planning")}>
            创建第一条学习计划
          </button>
        )}
        <div className="course-label">知识节点</div>
        {stage?.nodes.map((n) => (
          <button
            title={n.title}
            className={`side-item ${nodeId === n.node_id ? "active" : ""}`}
            key={n.node_id}
            onClick={() => selectNode(n.node_id)}
          >
            <span className="side-title">{n.title}</span>
            <small title="生成内容尚未完成学习核验">待学习</small>
          </button>
        ))}
        {!stage?.nodes.length && <p className="side-empty">暂无知识节点</p>}
        <div className="course-label">关联会话</div>
        <button
          className="side-item"
          title="会话功能尚未开放"
          onClick={() => navigate("conversations")}
        >
          <span className="side-title">阶段关联会话</span>
          <small>未开放</small>
        </button>
        <div className="course-label">阶段成果</div>
        <button className="side-item" onClick={() => navigate("summary")}>
          <span className="side-title">知识总结</span>
          <small>暂无</small>
        </button>
        {stage?.tasks.map((t) => (
          <button
            className="side-item"
            title={t.title}
            key={t.task_id}
            onClick={() => navigate("practice")}
          >
            <span className="side-title">{t.title}</span>
            <small>实践</small>
          </button>
        ))}
      </div>
      <div className="side-foot">以自己的节奏，循序推进。</div>
    </aside>
  );
}
