import { requestApi } from './client';

import type { components } from './generated/schema';

type DTO = components['schemas'];
export type PracticeChangeProjectView = DTO['PracticeChangeProjectView'];
export type PracticeChangeKnowledgeView = DTO['PracticeChangeKnowledgeView'];
export type PracticeChangeKnowledgeLink = DTO['PracticeChangeKnowledgeLink'];
export type PracticeChangeTaskView = DTO['PracticeChangeTaskView'];
export type PracticeChangeStageView = DTO['PracticeChangeStageView'];
export type PracticeChangeContextView = DTO['PracticeChangeContextView'];
export type PracticeChangeTaskRequest = DTO['PracticeChangeTaskRequest'];
export type PracticeChangeRequest = DTO['PracticeChangeRequest'];
export type PracticeChangeDecisionRequest = DTO['PracticeChangeDecisionRequest'];
export type PracticeChangeTaskDeltaView = DTO['PracticeChangeTaskDeltaView'];
export type PracticeChangeImpactView = DTO['PracticeChangeImpactView'];
export type PracticeChangePreviewView = DTO['PracticeChangePreviewView'];
export type PracticeChangeResultView = DTO['PracticeChangeResultView'];
const scope=(project:string)=>`?project_id=${encodeURIComponent(project)}`;
export const practiceChangeApi={
 context:(project:string)=>requestApi<PracticeChangeContextView>(`/practice-changes/context${scope(project)}`),
 preview:(project:string,body:PracticeChangeRequest)=>requestApi<PracticeChangePreviewView>(`/practice-changes${scope(project)}`,body),
 get:(project:string,id:string)=>requestApi<PracticeChangePreviewView>(`/practice-changes/${encodeURIComponent(id)}${scope(project)}`),
 decide:(project:string,id:string,action:'confirm'|'cancel',body:PracticeChangeDecisionRequest)=>requestApi<PracticeChangeResultView>(`/practice-changes/${encodeURIComponent(id)}/${action}${scope(project)}`,body),
};
