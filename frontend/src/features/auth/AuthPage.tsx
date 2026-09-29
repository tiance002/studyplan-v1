import { useState } from "react";
import { api } from "../../api/client";
import type { DTO } from "../../api/types";

export function AuthPage({
  onLogin,
}: {
  onLogin: (session: DTO["SessionView"]) => void;
}) {
  const [register, setRegister] = useState(false),
    [username, setUsername] = useState(""),
    [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  return (
    <div className="auth-page">
      <div className="auth-story">
        <div className="wordmark">
          Study Plan<span>学习工作室</span>
        </div>
        <h1>
          让每一步学习，
          <br />
          都有清晰的方向。
        </h1>
        <p>
          从一个目标开始，构建自己的学习路径。
          <br />
          查看资料、理解知识，再把它们变成作品。
        </p>
        <div className="auth-path">
          <span>01 设定目标</span>
          <span>02 确认路线</span>
          <span>03 开始学习</span>
        </div>
      </div>
      <form
        className="auth-card"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          try {
            onLogin(
              await (register ? api.register : api.login)({
                username,
                password,
              }),
            );
          } catch (err) {
            setError((err as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <p className="eyebrow">YOUR LEARNING SPACE</p>
        <h2>{register ? "创建你的学习空间" : "欢迎回来"}</h2>
        <p className="muted">
          {register
            ? "注册后即可创建第一条学习路线。"
            : "登录，继续自己的学习旅程。"}
        </p>
        <label>
          用户名
          <input
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            minLength={2}
            maxLength={32}
            required
            placeholder="支持中文用户名"
          />
        </label>
        <label>
          密码
          <input
            type="password"
            autoComplete={register ? "new-password" : "current-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={6}
            maxLength={12}
            required
            placeholder="6–12 位密码"
          />
        </label>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <button className="btn primary" disabled={busy}>
          {busy ? "正在处理…" : register ? "注册并进入" : "登录学习空间"}
        </button>
        <button
          className="text-button"
          type="button"
          onClick={() => {
            setRegister(!register);
            setError("");
          }}
        >
          {register ? "已有账号？返回登录" : "还没有账号？开放注册"}
        </button>
      </form>
    </div>
  );
}
