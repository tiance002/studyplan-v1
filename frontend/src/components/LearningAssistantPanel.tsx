export function LearningAssistantPanel({
  close,
  stageTitle,
}: {
  close: () => void;
  stageTitle: string;
}) {
  return (
    <aside className="assistant-panel" aria-label="学习助手">
      <div className="assistant-top">
        <span className="tutor-mark">✧</span>
        <div>
          <strong>学习助手</strong>
          <small>陪你理解，帮助你实践</small>
        </div>
        <button
          className="icon-button"
          aria-label="关闭学习助手"
          onClick={close}
        >
          ×
        </button>
      </div>
      <div className="assistant-context">
        <span className="pill">{stageTitle || "当前学习空间"}</span>
      </div>
      <div className="assistant-scroll">
        <p className="eyebrow">即将开放</p>
        <h3>把疑问留在学习现场</h3>
        <p className="muted">
          学习助手尚未开放。你可以先浏览学习节点、资源与实践要求。
        </p>
        <p className="muted">在学习过程中整理问题，后续可以与助手交流。</p>
      </div>
      <div className="assistant-compose">
        <textarea
          aria-label="助手输入框（尚未开放）"
          placeholder="学习助手尚未开放"
          disabled
        />
        <button className="btn" disabled>
          发送
        </button>
        <small>会话功能暂未开放</small>
      </div>
    </aside>
  );
}
