import { requestApi } from './client';
import type { components } from './generated/schema';

type DTO = components['schemas'];
export type PracticeSubmissionEvidenceRequest = DTO['PracticeSubmissionEvidenceRequest'];
export type PracticeSubmissionEvidenceView = DTO['PracticeSubmissionEvidenceView'];
export type PracticeSubmissionTaskView = DTO['PracticeSubmissionTaskView'];
export type PracticeSubmissionSnapshotView = DTO['PracticeSubmissionSnapshotView'];
export type PracticeSubmissionCoverageRequest = DTO['PracticeSubmissionCoverageRequest'];
export type PracticeSubmissionCoverageView = DTO['PracticeSubmissionCoverageView'];
export type PracticeSubmissionReviewView = DTO['PracticeSubmissionReviewView'];
export type PracticeSubmissionView = DTO['PracticeSubmissionView'];
export type PracticeSubmissionThreadView = DTO['PracticeSubmissionThreadView'];
export type PracticeSubmissionRequest = DTO['PracticeSubmissionRequest'];
export type PracticeSubmissionSaveView = DTO['PracticeSubmissionSaveView'];
export type PracticeSubmissionDecisionRequest = DTO['PracticeSubmissionDecisionRequest'];
export type PracticeSubmissionDecisionView = DTO['PracticeSubmissionDecisionView'];
export type PracticeSubmissionHistoryView = DTO['PracticeSubmissionHistoryView'];
export type PracticeOutcomeItemView = DTO['PracticeOutcomeItemView'];
export type PracticeOutcomeGroupView = DTO['PracticeOutcomeGroupView'];
export type PracticeOutcomeView = DTO['PracticeOutcomeView'];
export type ArtifactKind = PracticeSubmissionRequest['artifact_kind'];
export type EvidenceKind = PracticeSubmissionEvidenceRequest['kind'];
export type SubmissionTarget = Pick<PracticeSubmissionRequest, 'plan_id' | 'stage_id' | 'task_id'>;

const scope = (project: string) => `?project_id=${encodeURIComponent(project)}`;
export const submissionApi = {
  thread: (project: string, target: SubmissionTarget) => requestApi<PracticeSubmissionThreadView>(`/submissions${scope(project)}&${new URLSearchParams(target)}`),
  save: (project: string, body: PracticeSubmissionRequest) => requestApi<PracticeSubmissionSaveView>(`/submissions${scope(project)}`, body),
  get: (project: string, id: string) => requestApi<PracticeSubmissionView>(`/submissions/${encodeURIComponent(id)}${scope(project)}`),
  decide: (project: string, id: string, body: PracticeSubmissionDecisionRequest) => requestApi<PracticeSubmissionDecisionView>(`/submissions/${encodeURIComponent(id)}/decision${scope(project)}`, body),
  history: (project: string, cursor?: string) => requestApi<PracticeSubmissionHistoryView>(`/submissions/history${scope(project)}&limit=20${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`),
  outcomes: (project: string, cursor?: string) => requestApi<PracticeOutcomeView>(`/outcomes${scope(project)}&limit=20${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`),
};
