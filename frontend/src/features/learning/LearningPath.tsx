import type { DTO } from "../../api/types";
import { Resources } from "../../components/Resources";
export function LearningPath({
  workspace,
  enterStage,
  create,
}: {
  workspace: DTO["LearningWorkspaceView"] | null;
  enterStage: (id: string) => void;
  create: () => void;
}) {
  return (
    <div className="content">
      <p className="eyebrow">LEARNING PATH</p>
      <h1>你的学习路径</h1>
      <p className="lede">沿着清晰的阶段，从理解走向实践。</p>
      {workspace ? (
        <>
          <div className="goal-banner">
            <span className="pill">
              正式路线 · 版本 {workspace.plan.revision}
            </span>
            <h2>{workspace.plan.goal_snapshot}</h2>
            <p className="muted">
              {workspace.total_units} 个单元 · {workspace.completed_units}{" "}
              个已完成
            </p>
          </div>
          <div className="timeline">
            {workspace.stages.map((s) => (
              <section className="timeline-stage panel" key={s.stage.stage_id}>
                <span className="step">{s.stage.order_index + 1}</span>
                <div className="section-heading">
                  <h2>{s.stage.title}</h2>
                  <button
                    className="btn"
                    onClick={() => enterStage(s.stage.stage_id)}
                  >
                    进入学习 →
                  </button>
                </div>
                <p className="muted">{s.stage.objective}</p>
                <div className="chips">
                  {s.units.map((u) => (
                    <span className="pill" key={u.unit_id}>
                      {u.title}
                    </span>
                  ))}
                </div>
                <Resources items={s.resources} />
              </section>
            ))}
          </div>
        </>
      ) : (
        <div className="panel empty">
          <h2>还没有正式路线</h2>
          <p>先创建目标并确认草案，学习路径就会在这里展开。</p>
          <button className="btn primary" onClick={create}>
            创建学习目标
          </button>
        </div>
      )}
    </div>
  );
}
