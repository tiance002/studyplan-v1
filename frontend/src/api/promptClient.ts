import { requestApi } from './client';
import type { components } from './generated/schema';

type DTO = components['schemas'];
export type PromptTarget = Pick<DTO['PromptSaveRequest'], 'plan_id' | 'stage_id' | 'task_id'>;
export type PromptKnowledge = DTO['PromptKnowledgeView'];
export type PromptTask = DTO['PromptTaskView'];
export type PracticeProject = DTO['PromptPracticeProjectView'];
export type PromptReview = DTO['PromptReviewView'];
export type PromptRevision = DTO['PromptRevisionView'];
export type PromptThread = DTO['PromptThreadView'];
export type PromptSaveBody = DTO['PromptSaveRequest'];
export type PromptReviewBody = DTO['PromptReviewRequest'];
export type PromptCancelBody = DTO['PromptCancelRequest'];
export type PromptExportBody = DTO['PromptExportRequest'];
export type PromptRun = DTO['PromptReviewRunView'];
export type PromptExport = DTO['PromptExportView'];
const scope = (project: string) => `?project_id=${encodeURIComponent(project)}`;
export const promptApi = {
  thread: (project: string, target: PromptTarget) => requestApi<PromptThread>(`/prompts${scope(project)}&${new URLSearchParams(target)}`),
  save: (project: string, body: PromptSaveBody) => requestApi<DTO['PromptSaveView']>(`/prompts${scope(project)}`, body),
  revision: (project: string, id: string) => requestApi<PromptRevision>(`/prompts/revisions/${encodeURIComponent(id)}${scope(project)}`),
  history: (project: string, cursor?: string) => requestApi<DTO['PromptHistoryView']>(`/prompts/history${scope(project)}&limit=20${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`),
  review: (project: string, id: string, body: PromptReviewBody) => requestApi<PromptRun>(`/prompts/revisions/${encodeURIComponent(id)}/review${scope(project)}`, body),
  cancel: (project: string, id: string, body: PromptCancelBody) => requestApi<PromptRun>(`/prompts/revisions/${encodeURIComponent(id)}/cancel-review${scope(project)}`, body),
  export: (project: string, id: string, body: PromptExportBody) => requestApi<PromptExport>(`/prompts/revisions/${encodeURIComponent(id)}/exports${scope(project)}`, body),
  savedExport: (project: string, id: string) => requestApi<PromptExport>(`/prompts/exports/${encodeURIComponent(id)}${scope(project)}`),
};
