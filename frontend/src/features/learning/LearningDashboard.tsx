import type { DTO, Page } from "../../api/types";
import { Resources } from "../../components/Resources";
export function LearningDashboard({
  workspace,
  stageId,
  navigate,
  enterStage,
}: {
  workspace: DTO["LearningWorkspaceView"] | null;
  stageId: string;
  navigate: (p: Page) => void;
  enterStage: (id: string) => void;
}) {
  const stage =
    workspace?.stages.find((s) => s.stage.stage_id === stageId) ||
    workspace?.stages[0];
  return (
    <div className="dash-inner">
      <div className="dash-intro">
        <div>
          <p className="eyebrow">LEARNING STUDIO</p>
          <h1>今天，从这里继续。</h1>
          <p className="muted">给目标留出时间，把知识变成自己的能力。</p>
        </div>
        <button className="btn" onClick={() => navigate("planning")}>
          ＋ 创建学习目标
        </button>
      </div>
      {workspace ? (
        <section className="dash-feature">
          <div>
            <span className="pill">
              当前学习计划 · v{workspace.plan.revision}
            </span>
            <h2>{workspace.plan.goal_snapshot}</h2>
            <p className="muted">
              {workspace.stages.length} 个阶段 · {workspace.completed_units}/
              {workspace.total_units} 个学习单元完成
            </p>
            <div className="progress-track">
              <span
                style={{
                  width: `${workspace.total_units ? (workspace.completed_units / workspace.total_units) * 100 : 0}%`,
                }}
              />
            </div>
          </div>
          <div className="feature-side">
            <p className="eyebrow">下一步学习</p>
            <h3>{stage?.stage.title}</h3>
            <p className="muted">{stage?.stage.objective}</p>
            {stage && (
              <button
                className="btn primary"
                onClick={() => enterStage(stage.stage.stage_id)}
              >
                进入阶段学习 →
              </button>
            )}
          </div>
        </section>
      ) : (
        <section className="dash-feature">
          <div>
            <span className="pill">从一个目标开始</span>
            <h2>为你的学习，建立一条清晰的路线。</h2>
            <p className="muted">
              生成草案、查看完整阶段、调整目标，再确认发布。
            </p>
          </div>
          <button className="btn primary" onClick={() => navigate("planning")}>
            创建第一条计划 →
          </button>
        </section>
      )}
      <div className="dash-grid">
        <section className="panel">
          <div className="section-heading">
            <h2>学习资料</h2>
            <span className="pill">当前阶段</span>
          </div>
          <Resources items={stage?.resources ?? []} />
        </section>
        <section className="panel">
          <div className="section-heading">
            <h2>今日学习</h2>
            <span className="muted">按自己的节奏</span>
          </div>
          {stage?.units.length ? (
            stage.units.map((u) => (
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
            ))
          ) : (
            <p className="empty">确认计划后，查看当前阶段的学习单元。</p>
          )}
        </section>
        <section className="panel">
          <div className="section-heading">
            <h2>学习路径</h2>
            <button className="text-button" onClick={() => navigate("path")}>
              查看完整路线 →
            </button>
          </div>
          {workspace?.stages.map((s) => (
            <button
              className="path-row"
              key={s.stage.stage_id}
              onClick={() => enterStage(s.stage.stage_id)}
            >
              <span className="step">{s.stage.order_index + 1}</span>
              <strong>{s.stage.title}</strong>
              <span>→</span>
            </button>
          )) || <p className="empty">你的正式学习路线将在这里展开。</p>}
        </section>
        <section className="panel">
          <div className="section-heading">
            <h2>项目实践</h2>
            <button
              className="text-button"
              onClick={() => navigate("practice")}
            >
              查看实践 →
            </button>
          </div>
          {stage?.tasks.length ? (
            stage.tasks.map((t) => (
              <div className="practice-card" key={t.task_id}>
                <span className="practice-icon">⌘</span>
                <div>
                  <h3>{t.title}</h3>
                  <p className="muted">{t.goal}</p>
                </div>
              </div>
            ))
          ) : (
            <p className="empty">
              当前阶段暂无实践任务。可以在完整路径中浏览后续阶段。
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
