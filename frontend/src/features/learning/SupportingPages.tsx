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
export { PromptPage as PracticeDetail } from './PromptPage';
