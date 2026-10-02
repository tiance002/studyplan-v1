import type { components } from "./generated/schema";
export type DTO = components["schemas"];
export type Page =
  | "dashboard"
  | "planning"
  | "path"
  | "workspace"
  | "summary"
  | "practice"
  | "conversations"
  | "settings";
export type Plan = DTO["PlanView"];
export type StageWorkspace = DTO["StageWorkspaceView"];
export type ResourceTarget = Pick<DTO['ResourceSearchRequest'], 'plan_id' | 'stage_id' | 'unit_id' | 'node_id'>;
export type ResourceSearch = DTO['ResourceSearchView'];
export type ResourceInspection = DTO['ResourceInspectionView'];
export type ResourceInspectionRequest = DTO['ResourceInspectionRequest'];
export type ResourceCandidate = DTO['ResourceCandidateView'];
