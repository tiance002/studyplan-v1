import type { components } from "./generated/schema";
import type { ResourceInspection, ResourceInspectionRequest, ResourceTarget } from './types';

type DTO = components["schemas"];
export type SummarySaveBody = DTO['SummarySaveRequest'];
export type SummaryTarget = Pick<SummarySaveBody, 'plan_id' | 'stage_id' | 'unit_id'>;
export type SummaryReview = DTO['SummaryReviewView'];
export type SummaryAttempt = DTO['SummaryAttemptView'];
export type SummaryThread = DTO['SummaryThreadView'];
export type SummarySave = DTO['SummarySaveView'];
export type SummaryReviewBody = DTO['SummaryReviewRequest'];
export type SummaryReviewRun = DTO['SummaryReviewRunView'];
export type SummaryCancelBody = DTO['SummaryCancelRequest'];
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
export { request as requestApi };
const resourceScope = (project: string, target: ResourceTarget) =>
  `${scope(project)}&${new URLSearchParams({plan_id:target.plan_id,stage_id:target.stage_id,unit_id:target.unit_id})}${target.node_id ? `&node_id=${encodeURIComponent(target.node_id)}` : ''}`;
export const api = {
  planChangeContext: (project: string) => request<DTO['PlanChangeContext']>(`/plan-changes/context${scope(project)}`),
  previewPlanChange: (project: string, body: DTO['PlanChangeRequest']) => request<DTO['PlanChangePreviewView']>(`/plan-changes${scope(project)}`, body),
  planChange: (project: string, id: string) => request<DTO['PlanChangePreviewView']>(`/plan-changes/${encodeURIComponent(id)}${scope(project)}`),
  confirmPlanChange: (project: string, id: string, body: DTO['PlanChangeDecisionRequest']) => request<DTO['PlanChangeResult']>(`/plan-changes/${encodeURIComponent(id)}/confirm${scope(project)}`, body),
  cancelPlanChange: (project: string, id: string, body: DTO['PlanChangeDecisionRequest']) => request<DTO['PlanChangeResult']>(`/plan-changes/${encodeURIComponent(id)}/cancel${scope(project)}`, body),
  summaryThread: (project: string, target: SummaryTarget) => request<SummaryThread>(`/summaries${scope(project)}&${new URLSearchParams(Object.entries(target).filter(([,value]) => value != null) as [string,string][])}`),
  saveSummary: (project: string, body: SummarySaveBody) => request<SummarySave>(`/summaries${scope(project)}`, body),
  summaryAttempt: (project: string, id: string) => request<SummaryAttempt>(`/summaries/attempts/${encodeURIComponent(id)}${scope(project)}`),
  reviewSummary: (project: string, id: string, body: SummaryReviewBody) => request<SummaryReviewRun>(`/summaries/attempts/${encodeURIComponent(id)}/review${scope(project)}`, body),
  cancelSummaryReview: (project: string, id: string, body: SummaryCancelBody) => request<SummaryReviewRun>(`/summaries/attempts/${encodeURIComponent(id)}/cancel-review${scope(project)}`, body),
  summaryHistory: (project: string, cursor?: string) => request<DTO['SummaryHistoryView']>(`/summaries/history${scope(project)}&limit=20${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`),
  resourceChangeCatalog: (project: string) => request<DTO['ResourceCatalogView'][]>(`/resource-changes/catalog${scope(project)}`),
  previewResourceChange: (project: string, body: DTO['ResourceChangeRequest']) => request<DTO['ResourceChangePreviewView']>(`/resource-changes${scope(project)}`, body),
  resourceChange: (project: string, id: string) => request<DTO['ResourceChangePreviewView']>(`/resource-changes/${encodeURIComponent(id)}${scope(project)}`),
  decideResourceChange: (project: string, id: string, action: 'confirm' | 'cancel', body: DTO['ResourceChangeDecisionRequest']) => request<DTO['ResourceChangeResultView']>(`/resource-changes/${encodeURIComponent(id)}/${action}${scope(project)}`, body),
  listExposures: (project: string, plan: string, stage: string) =>
    request<DTO['ExposureView'][]>(`/exposures${scope(project)}&${new URLSearchParams({plan_id: plan, stage_id: stage})}`),
  changeExposure: (project: string, body: DTO['ExposureChangeRequest']) =>
    request<DTO['ExposureChangeView']>(`/exposures${scope(project)}`, body, 'PUT'),
  exposureHistory: (project: string, target: Pick<DTO['ExposureChangeRequest'], 'plan_id' | 'stage_id' | 'unit_id'>) =>
    request<DTO['ExposureEventView'][]>(`/exposures/history${resourceScope(project, target)}`),
  resourcePreferences: (project: string, target: Pick<DTO['PreferencePutRequest'], 'plan_id' | 'stage_id' | 'unit_id' | 'node_id'>) =>
    request<DTO['PreferenceContextView']>(`/preferences${resourceScope(project, target)}`),
  saveResourcePreference: (project: string, body: DTO['PreferencePutRequest']) =>
    request<DTO['PreferenceContextView']>(`/preferences${scope(project)}`, body, 'PUT'),
  restoreResourcePreference: (project: string, body: DTO['PreferenceDeleteRequest']) =>
    request<DTO['PreferenceContextView']>(`/preferences${scope(project)}`, body, 'DELETE'),
  searchResources: (project: string, body: DTO['ResourceSearchRequest']) =>
    request<DTO['ResourceSearchView']>(`/resources/searches${scope(project)}`,
      body.source === 'web' ? Object.fromEntries(Object.entries(body).filter(([key]) => key !== 'source')) : body),
  resourceSearch: (project: string, id: string, target: ResourceTarget) =>
    request<DTO['ResourceSearchView']>(`/resources/searches/${encodeURIComponent(id)}${resourceScope(project, target)}`),
  resourceSearchByKey: (project: string, key: string, target: ResourceTarget) =>
    request<DTO['ResourceSearchView']>(`/resources/searches/by-key/${encodeURIComponent(key)}${resourceScope(project, target)}`),
  inspectResource: (project: string, body: ResourceInspectionRequest) =>
    request<ResourceInspection>(`/resources/inspections${scope(project)}`, body),
  resourceInspection: (project: string, id: string, target: ResourceTarget) =>
    request<ResourceInspection>(`/resources/inspections/${encodeURIComponent(id)}${resourceScope(project, target)}`),
  resourceInspectionByKey: (project: string, key: string, target: ResourceTarget) =>
    request<ResourceInspection>(`/resources/inspections/by-key/${encodeURIComponent(key)}${resourceScope(project, target)}`),
  selectedResources: (project: string, target: ResourceTarget) =>
    request<DTO['SelectedResourceView'][]>(`/resources/selections${resourceScope(project, target)}`),
  selectResource: (project: string, body: DTO['ResourceSelectionRequest']) =>
    request<DTO['SelectedResourceView']>(`/resources/selections${scope(project)}`,
      !body.module_keys?.length && !body.chapter_paths?.length && body.role === 'reference'
        ? Object.fromEntries(Object.entries(body).filter(([key]) => key !== 'role')) : body),
  manualResource: (project: string, body: DTO['ManualResourceRequest']) =>
    request<DTO['SelectedResourceView']>(`/resources/manual${scope(project)}`,
      Object.fromEntries(Object.entries(body).filter(([key]) => key !== 'node_id'))),
  removeResource: (project: string, id: string, target: ResourceTarget) =>
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
  generate: (project: string, goal: string, goalSpec?: DTO['GoalSpec'] | null) =>
    request<DTO["PlanGenerateResponse"]>(`/plans/generate${scope(project)}`, {
      goal,
      ...(goalSpec ? { goal_spec: goalSpec } : {}),
    } satisfies DTO["PlanGenerateRequest"]),
  generatePlanChange: (project: string, body: DTO['GeneratedPlanChangeRequest']) =>
    request<DTO['PlanGenerateResponse']>(`/plan-changes/generate${scope(project)}`, body),
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
