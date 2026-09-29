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
