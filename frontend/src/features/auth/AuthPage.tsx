import { useState } from "react";
import { api, ApiError } from "../../api/client";
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
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const switchMode = (next: boolean) => {
    if (busy) return;
    setRegister(next);
    setError("");
  };
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
        noValidate
        onSubmit={async (e) => {
          e.preventDefault();
          if (busy) return;
          setErrorStatus(null);
          const normalizedUsername = username.normalize("NFKC").trim();
          if (
            Array.from(normalizedUsername).length < 2 ||
            Array.from(normalizedUsername).length > 32 ||
            !/^[A-Za-z\u3400-\u9fff][A-Za-z0-9_\u3400-\u9fff-]*$/.test(normalizedUsername)
          ) {
            setError("用户名须为 2–32 个字符，以汉字或字母开头，仅支持汉字、字母、数字、下划线和短横线。");
            return;
          }
          const passwordLength = Array.from(password).length;
          if (Array.from(password).some((character) => /^[\uD800-\uDFFF]$/.test(character))) {
            setError("密码含非法字符，请检查后重试。");
            return;
          }
          if (passwordLength < (register ? 6 : 1) || passwordLength > (register ? 12 : 128)) {
            setError(register ? "新密码须为 6–12 个字符，支持粘贴，无需混合特定字符。" : "请输入原有密码，最多 128 个字符。");
            return;
          }
          setBusy(true);
          setError("");
          try {
            onLogin(
              await (register ? api.register : api.login)({
                username: normalizedUsername,
                password,
              }),
            );
          } catch (err) {
            setErrorStatus(err instanceof ApiError ? err.status : null);
            if (err instanceof ApiError && err.status === 401 && !register) {
              setError("登录失败：用户名或密码不正确，请检查后重试。若尚未注册，请先点击“立即注册”创建账号。");
            } else if (err instanceof ApiError && err.status === 409 && register) {
              setError("这个用户名已被使用。如果是你的账号，请切换到登录；也可以更换用户名后注册。");
            } else if (err instanceof ApiError && err.status === 422) {
              setError(register
                ? "请检查输入：用户名为 2–32 个字符，新密码为 6–12 个字符。用户名须以汉字或字母开头，且不能包含空格。"
                : "请检查输入：用户名为 2–32 个字符，原有密码不能为空且最多 128 个字符。");
            } else {
              setError(err instanceof Error ? err.message : "操作失败，请稍后重试。");
            }
          } finally {
            setBusy(false);
          }
        }}
      >
        <p className="eyebrow">YOUR LEARNING SPACE</p>
        <div className="auth-modes" role="group" aria-label="账号入口">
          <button type="button" aria-pressed={!register} disabled={busy} onClick={() => switchMode(false)}>登录</button>
          <button type="button" aria-pressed={register} disabled={busy} onClick={() => switchMode(true)}>注册</button>
        </div>
        <h2>{register ? "创建你的学习空间" : "欢迎回来"}</h2>
        <p className="muted">
          {register
            ? "首次使用？创建账号后即可开始，无需邀请码。"
            : "已有账号请登录；首次使用请点击上方“注册”。"}
        </p>
        <label>
          用户名
          <input
            aria-label="用户名"
            aria-describedby={register ? "username-hint" : undefined}
            autoComplete="username"
            value={username}
            disabled={busy}
            onChange={(e) => { setUsername(e.target.value); setError(""); }}
            minLength={2}
            required
            placeholder="支持中文用户名"
          />
          {register && <span id="username-hint" className="auth-hint">2–32 个字符，以汉字或字母开头；可含数字、下划线和短横线。</span>}
        </label>
        <label>
          密码
          <input
            aria-label="密码"
            aria-describedby={register ? "password-hint" : undefined}
            type="password"
            autoComplete={register ? "new-password" : "current-password"}
            value={password}
            disabled={busy}
            onChange={(e) => { setPassword(e.target.value); setError(""); }}
            required
            placeholder={register ? "6–12 个字符，支持粘贴" : "输入原有密码"}
          />
          {register && <span id="password-hint" className="auth-hint">6–12 个字符，支持粘贴，无需混合特定字符。请记住密码以便下次登录。</span>}
        </label>
        {error && (
          <div role="alert" className="error">
            {error}
            {((register && errorStatus === 409) || (!register && errorStatus === 401)) && (
              <button type="button" className="text-button" disabled={busy} onClick={() => switchMode(!register)}>
                {register ? "返回登录" : "立即注册"}
              </button>
            )}
          </div>
        )}
        <button className="btn primary" disabled={busy}>
          {busy ? "正在处理…" : register ? "注册并进入" : "登录学习空间"}
        </button>
        <button
          className="text-button"
          type="button"
          disabled={busy}
          onClick={() => switchMode(!register)}
        >
          {register ? "已有账号？返回登录" : "还没有账号？立即注册"}
        </button>
      </form>
    </div>
  );
}
