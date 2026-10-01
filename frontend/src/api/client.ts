import type { components } from "./generated/schema";

type DTO = components["schemas"];
let csrfToken = "";
export const setCsrfToken = (token: string) => {
  csrfToken = token;
};
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
async function request<T>(
  url: string,
  body?: unknown,
  method?: string,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/v1${url}`, {
      method: method ?? (body === undefined ? "GET" : "POST"),
      credentials: "include",
      headers: {
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
        ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "无法连接服务，请检查网络连接后重试。");
  }
  const data = await response.json().catch(() => null);
  if (!response.ok)
    throw new ApiError(
      response.status,
      data?.message ??
        (response.status >= 500
          ? "服务暂时不可用，请稍后重试。"
          : typeof data?.detail === "string"
            ? data.detail
            : `请求失败（${response.status}），请检查输入或重新加载。`),
    );
  if (data === null)
    throw new ApiError(response.status, "服务返回了无法读取的内容，请稍后重试。");
  return data as T;
}
const scope = (project: string) => `?project_id=${encodeURIComponent(project)}`;
export const api = {
  modelSettings: () => request<DTO["ModelSettingsResponse"]>("/model-settings"),
  saveModelSettings: (body: DTO["ModelSettingsRequest"]) =>
    request<DTO["ModelSettingsResponse"]>("/model-settings", body, "PUT"),
  clearModelSettings: (expected_version: number) =>
    request<DTO["ModelSettingsResponse"]>(
      "/model-settings",
      { expected_version } satisfies DTO["ModelSettingsClear"],
      "DELETE",
    ),
  session: () => request<DTO["SessionView"]>("/session"),
  entryMode: () => request<DTO["SessionEntryMode"]>("/session/entry-mode"),
  enterLocal: () => request<DTO["SessionView"]>("/session/local", {}),
  login: (body: DTO["CredentialsRequest"]) =>
    request<DTO["SessionView"]>("/auth/login", body),
  register: (body: DTO["CredentialsRequest"]) =>
    request<DTO["SessionView"]>("/auth/register", body),
  logout: () => request<{ logged_out: boolean }>("/auth/logout", {}),
  workspace: (project: string) =>
    request<DTO["LearningWorkspaceView"]>(`/workspace${scope(project)}`).catch(
      (err) => {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      },
    ),
  health: async () => {
    const r = await fetch("/healthz");
    if (!r.ok) throw new Error("无法读取服务状态");
    const h = await r.json();
    return { fake_llm: h.llm_provider === "fake" };
  },
  generate: (project: string, goal: string) =>
    request<DTO["PlanGenerateResponse"]>(`/plans/generate${scope(project)}`, {
      goal,
    } satisfies DTO["PlanGenerateRequest"]),
  run: (project: string, id: string) =>
    request<DTO["RunView"]>(`/runs/${encodeURIComponent(id)}${scope(project)}`),
  draft: (project: string, id: string) =>
    request<DTO["PlanDraftView"]>(
      `/plans/drafts/${encodeURIComponent(id)}${scope(project)}`,
    ),
  current: (project: string) =>
    request<DTO["PlanView"] | null>(`/plans/current${scope(project)}`).catch(
      (err) => {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      },
    ),
  decide: (project: string, id: string, body: DTO["DraftDecisionRequest"]) =>
    request<DTO["PlanDecisionResponse"]>(
      `/plans/drafts/${encodeURIComponent(id)}/decision${scope(project)}`,
      body,
    ),
};

export async function restoreSession(onMode: (local: boolean) => void): Promise<DTO["SessionView"]> {
  const mode = await api.entryMode();
  onMode(mode.local_entry_enabled);
  try {
    return await api.session();
  } catch (error) {
    if (mode.local_entry_enabled && error instanceof ApiError && error.status === 401)
      return api.enterLocal();
    throw error;
  }
}
