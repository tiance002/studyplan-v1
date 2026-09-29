import { useEffect, useState } from "react";
import { api, ApiError } from "./api/client";
import type { components } from "./api/generated/schema";

type Settings = components["schemas"]["ModelSettingsResponse"];

export function ModelSettings({
  onChange,
}: {
  onChange: (value: Settings) => void;
}) {
  const [current, setCurrent] = useState<Settings | null>(null);
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  function accept(value: Settings) {
    setCurrent(value);
    setBaseUrl(value.base_url);
    setModel(value.model_id);
    setKey("");
    onChange(value);
  }
  useEffect(() => {
    api
      .modelSettings()
      .then(accept)
      .catch((err) => setError(err.message));
  }, []);
  async function save(clear = false) {
    if (!current) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      accept(
        clear
          ? await api.clearModelSettings(current.version)
          : await api.saveModelSettings({
              expected_version: current.version,
              base_url: baseUrl,
              model_id: model,
              protocol: "openai",
              api_key: key,
            }),
      );
      setMessage(
        clear
          ? "个人配置已清除，历史路线保留。"
          : "个人配置已保存，没有发起模型调用。",
      );
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        try {
          accept(await api.modelSettings());
        } catch {
          /* Preserve the original conflict message. */
        }
        setError("配置已被其他窗口修改，已加载最新版本，请重新检查。");
      } else setError(err instanceof Error ? err.message : "配置操作失败");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="model-block">
      {current && (
        <p className="model-source">
          当前使用：
          {current.source === "personal"
            ? "个人模型"
            : current.source === "deployment"
              ? "部署默认模型"
              : "未配置模型"}
          {current.model_id && ` · ${current.model_id}`}
        </p>
      )}
      <details>
        <summary>模型设置</summary>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            save();
          }}
        >
          <p className="hint">
            仅支持 OpenAI 兼容 API。密钥加密保存在服务端，保存后不回显。
          </p>
          <label htmlFor="model-base">Base URL</label>
          <input
            id="model-base"
            type="url"
            placeholder="https://api.deepseek.com"
            value={baseUrl}
            onChange={(event) => setBaseUrl(event.target.value)}
            required
            disabled={busy}
          />
          <label htmlFor="model-name">模型名称</label>
          <input
            id="model-name"
            placeholder="服务商提供的模型名称"
            value={model}
            onChange={(event) => setModel(event.target.value)}
            required
            disabled={busy}
          />
          <label htmlFor="model-key">
            API Key {current?.has_api_key ? "（留空保留已保存密钥）" : ""}
          </label>
          <input
            id="model-key"
            type="password"
            autoComplete="off"
            value={key}
            onChange={(event) => setKey(event.target.value)}
            required={!current?.has_api_key}
            disabled={busy}
          />
          {current && (
            <p className="scope-note">
              可用主机：{current.allowed_hosts.join("、")}。
              {!current.encryption_available &&
                "部署管理员尚未配置密钥加密，暂时不能保存个人配置。"}
            </p>
          )}
          <div className="model-actions">
            <button
              className="btn primary"
              disabled={busy || !current?.encryption_available}
            >
              {busy ? "正在保存…" : "保存模型设置"}
            </button>
            <button
              type="button"
              className="btn quiet"
              disabled={busy || !current?.has_api_key}
              onClick={() => save(true)}
            >
              清除个人配置
            </button>
          </div>
          <p className="hint">
            生成将产生服务商费用。修改配置只影响新运行，历史路线保留。
          </p>
        </form>
      </details>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {message && (
        <p className="notice" role="status">
          {message}
        </p>
      )}
    </div>
  );
}
