import type { StageWorkspace } from "../../api/types";
export function ConversationList() {
  return (
    <div className="content">
      <p className="eyebrow">CONVERSATIONS</p>
      <h1>我的会话</h1>
      <p className="lede">把学习中的问题和思考留在这里。</p>
      <div className="tabs">
        <span className="tab active">全部会话</span>
        <span className="tab">阶段会话</span>
      </div>
      <div className="panel empty">
        <h2>会话功能尚未开放</h2>
        <p>尚未开放会话功能。开通后，你的学习交流会保存在这里。</p>
      </div>
    </div>
  );
}
export { SummaryPage as SummaryDetail } from './SummaryPage';
export function PracticeDetail({
  stage,
}: {
  stage: StageWorkspace | undefined;
}) {
  return (
    <div className="content">
      <p className="eyebrow">PROJECT PRACTICE</p>
      <h1>项目实践</h1>
      <p className="lede">通过一个可验收的作品，把知识用起来。</p>
      <div className="tabs">
        <span className="tab active">实践要求</span>
        <span className="tab">交付与评审 · 未开放</span>
      </div>
      {stage?.tasks.length ? (
        stage.tasks.map((t) => (
          <section className="panel practice-detail" key={t.task_id}>
            <span className="pill warm">
              {t.status === "accepted" ? "已验收" : "待实践"}
            </span>
            <h2>{t.title}</h2>
            <div className="kvline">
              <span>实践目标</span>
              <p>{t.goal}</p>
            </div>
            <div className="kvline">
              <span>实施范围</span>
              <p>{t.in_scope?.join("、") || "尚未补充"}</p>
            </div>
            <div className="kvline">
              <span>范围之外</span>
              <p>{t.out_scope?.join("、") || "尚未补充"}</p>
            </div>
            <div className="kvline">
              <span>验收标准</span>
              <ul>
                {t.acceptance.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            </div>
            <p className="form-note">
              任务来自正式计划关联。本批次提供只读要求，提交与评审尚未开放。
            </p>
          </section>
        ))
      ) : (
        <div className="panel empty">
          <h2>当前阶段暂无实践任务</h2>
          <p>切换阶段，浏览正式计划分配的实践要求。</p>
        </div>
      )}
    </div>
  );
}
