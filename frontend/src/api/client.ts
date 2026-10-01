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
const resourceScope = (project: string, target: Pick<DTO['ResourceSearchRequest'], 'plan_id' | 'stage_id' | 'unit_id'>) =>
  `${scope(project)}&${new URLSearchParams({plan_id:target.plan_id,stage_id:target.stage_id,unit_id:target.unit_id})}`;
export const api = {
  listExposures: (project: string, plan: string, stage: string) =>
    request<DTO['ExposureView'][]>(`/exposures${scope(project)}&${new URLSearchParams({plan_id: plan, stage_id: stage})}`),
  changeExposure: (project: string, body: DTO['ExposureChangeRequest']) =>
    request<DTO['ExposureChangeView']>(`/exposures${scope(project)}`, body, 'PUT'),
  exposureHistory: (project: string, target: Pick<DTO['ExposureChangeRequest'], 'plan_id' | 'stage_id' | 'unit_id'>) =>
    request<DTO['ExposureEventView'][]>(`/exposures/history${resourceScope(project, target)}`),
  resourcePreferences: (project: string, target: Pick<DTO['PreferencePutRequest'], 'plan_id' | 'stage_id' | 'unit_id' | 'node_id'>) =>
    request<DTO['PreferenceContextView']>(`/preferences${resourceScope(project, target)}${target.node_id ? `&node_id=${encodeURIComponent(target.node_id)}` : ''}`),
  saveResourcePreference: (project: string, body: DTO['PreferencePutRequest']) =>
    request<DTO['PreferenceContextView']>(`/preferences${scope(project)}`, body, 'PUT'),
  restoreResourcePreference: (project: string, body: DTO['PreferenceDeleteRequest']) =>
    request<DTO['PreferenceContextView']>(`/preferences${scope(project)}`, body, 'DELETE'),
  searchResources: (project: string, body: DTO['ResourceSearchRequest']) =>
    request<DTO['ResourceSearchView']>(`/resources/searches${scope(project)}`, body),
  resourceSearch: (project: string, id: string, target: Pick<DTO['ResourceSearchRequest'], 'plan_id' | 'stage_id' | 'unit_id'>) =>
    request<DTO['ResourceSearchView']>(`/resources/searches/${encodeURIComponent(id)}${resourceScope(project, target)}`),
  resourceSearchByKey: (project: string, key: string, target: Pick<DTO['ResourceSearchRequest'], 'plan_id' | 'stage_id' | 'unit_id'>) =>
    request<DTO['ResourceSearchView']>(`/resources/searches/by-key/${encodeURIComponent(key)}${resourceScope(project, target)}`),
  selectedResources: (project: string, target: Pick<DTO['ResourceSearchRequest'], 'plan_id' | 'stage_id' | 'unit_id'>) =>
    request<DTO['SelectedResourceView'][]>(`/resources/selections${resourceScope(project, target)}`),
  selectResource: (project: string, body: DTO['ResourceSelectionRequest']) =>
    request<DTO['SelectedResourceView']>(`/resources/selections${scope(project)}`, body),
  manualResource: (project: string, body: DTO['ManualResourceRequest']) =>
    request<DTO['SelectedResourceView']>(`/resources/manual${scope(project)}`, body),
  removeResource: (project: string, id: string, target: Pick<DTO['ResourceSearchRequest'], 'plan_id' | 'stage_id' | 'unit_id'>) =>
    request<DTO['ResourceRemovalView']>(`/resources/selections/${encodeURIComponent(id)}${resourceScope(project, target)}`, undefined, 'DELETE'),
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
  login: (body: DTO["LoginRequest"]) =>
    request<DTO["SessionView"]>("/auth/login", body),
  register: (body: DTO["RegistrationRequest"]) =>
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
