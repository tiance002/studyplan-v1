import type { DTO, ResourceInspection, ResourceInspectionRequest, ResourceSearch, ResourceTarget } from '../../api/types';

export type InspectionBuffer = { pending: ResourceInspectionRequest; view: ResourceInspection | null };
export type ResourceBufferState = {
  query: string;
  source: 'web' | 'github';
  pending: DTO['ResourceSearchRequest'] | null;
  search: ResourceSearch | null;
  inspections: Record<string, InspectionBuffer>;
  mappings: Record<string, {moduleKey:string; chapterPath:string; role:'primary'|'supplement'|'comparison'|'reference'|'case_study'|'practice'}>;
  selected: DTO['SelectedResourceView'][];
  title: string;
  url: string;
  error: string;
  busy: boolean;
  notSubmitted: boolean;
};

const buffers = new Map<string, ResourceBuffer>();
export class ResourceBuffer {
  active = true;
  readSequence = 0;
  private listeners = new Set<() => void>();
  private state: ResourceBufferState = { query:'', source:'web', pending:null, search:null, inspections:{}, mappings:{}, selected:[], title:'', url:'', error:'', busy:false, notSubmitted:false };
  constructor(readonly actorKey: string) {}
  snapshot = () => this.state;
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; };
  update(patch: Partial<ResourceBufferState>) {
    if (!this.active) return;
    this.state = { ...this.state, ...patch };
    this.listeners.forEach(listener => listener());
  }
}

export function resourceBuffer(actorKey: string, projectId: string, target: ResourceTarget, nodeId?: string) {
  const key = JSON.stringify([actorKey, projectId, target.plan_id, target.stage_id, target.unit_id, nodeId || '']);
  let buffer = buffers.get(key);
  if (!buffer) { buffer = new ResourceBuffer(actorKey); buffers.set(key, buffer); }
  return buffer;
}

// The auth owner calls this after successful logout. Invalidation also fences late responses.
export function clearResourceBuffers(actorKey?: string) {
  for (const [key, buffer] of buffers) {
    if (actorKey === undefined || buffer.actorKey === actorKey) {
      buffer.active = false;
      ++buffer.readSequence;
      buffers.delete(key);
    }
  }
}
