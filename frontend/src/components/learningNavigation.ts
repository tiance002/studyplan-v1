import type { Page } from '../api/types';
export function toggleStage(expanded: string | null, stage: string): string | null { return expanded === stage ? null : stage; }
export function stagePage(page: Page, external = false): Page { return !external && (page === 'practice' || page === 'summary') ? page : 'workspace'; }

export type PracticeTaskIntent = { stageId: string; taskId: string; sequence: number };
export function taskSelectionForIntent(
  stageId: string,
  tasks: { task_id: string }[],
  intent: PracticeTaskIntent | undefined,
  appliedSequence: number,
): string | undefined {
  if (!intent || intent.sequence === appliedSequence || intent.stageId !== stageId) return undefined;
  return tasks.some(task => task.task_id === intent.taskId) ? intent.taskId : undefined;
}

export function stageCompletionLabel(stage: unknown): '已完成' | '未完成' {
  if (!stage || typeof stage !== 'object' || !('completion' in stage)) return '未完成';
  const completion = stage.completion;
  return completion && typeof completion === 'object' && 'status' in completion && completion.status === 'completed' ? '已完成' : '未完成';
}
export function stageTotals(workspace: unknown): { completed: number; total: number } {
  if (!workspace || typeof workspace !== 'object') return { completed: 0, total: 0 };
  const value = workspace as { completed_stages?: unknown; total_stages?: unknown; stages?: unknown };
  const fallbackTotal = Array.isArray(value.stages) ? value.stages.length : 0;
  const total = typeof value.total_stages === 'number' && Number.isFinite(value.total_stages) ? Math.max(0, value.total_stages) : fallbackTotal;
  const completed = typeof value.completed_stages === 'number' && Number.isFinite(value.completed_stages) ? Math.max(0, Math.min(total, value.completed_stages)) : 0;
  return { completed, total };
}
