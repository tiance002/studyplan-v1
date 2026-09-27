import React from "react";
import { createRoot } from "react-dom/client";

// B1 骨架：仅证明 Vite/TS/React 链路可运行。
// 真正的业务界面属 B6（前后端联调），本阶段不做 UI。
// 前端**不得**自行定义业务状态、图内部节点或自报用户身份（ADR-0004）。
const App = () => (
  <main style={{ fontFamily: "system-ui, sans-serif", padding: 24 }}>
    <h1>学习规划助手 V1.1</h1>
    <p>B1 骨架：前端链路就绪，业务界面待 B6 实现。</p>
    <p>
      契约来源：后端导出的 OpenAPI（<code>npm run gen:api</code>）。
    </p>
  </main>
);

const container = document.getElementById("root");
if (container) {
  createRoot(container).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
}
