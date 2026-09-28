import type { components } from "./generated/schema";

type DTO = components["schemas"];
export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
async function request<T>(url: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api/v1${url}`, {
    method: body === undefined ? "GET" : "POST", credentials: "include",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new ApiError(response.status, data.message ?? data.detail ?? `请求失败（${response.status}）`);
  return data as T;
}
const scope = (project: string) => `?project_id=${encodeURIComponent(project)}`;
export const api = {
  session: () => request<DTO["SessionView"]>("/session"),
  enter: (token: string) => request<DTO["SessionView"]>("/session", { token } satisfies DTO["SessionEntry"]),
  generate: (project: string, goal: string) => request<DTO["PlanGenerateResponse"]>(`/plans/generate${scope(project)}`, { goal } satisfies DTO["PlanGenerateRequest"]),
  run: (project: string, id: string) => request<DTO["RunView"]>(`/runs/${encodeURIComponent(id)}${scope(project)}`),
  draft: (project: string, id: string) => request<DTO["PlanDraftView"]>(`/plans/drafts/${encodeURIComponent(id)}${scope(project)}`),
  current: (project: string) => request<DTO["PlanView"] | null>(`/plans/current${scope(project)}`).catch(err => { if (err instanceof ApiError && err.status === 404) return null; throw err; }),
  decide: (project: string, id: string, body: DTO["DraftDecisionRequest"]) => request<DTO["PlanDecisionResponse"]>(`/plans/drafts/${encodeURIComponent(id)}/decision${scope(project)}`, body),
};
