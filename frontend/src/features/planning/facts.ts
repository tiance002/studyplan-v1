// Display adapters consume frozen server facts; they never infer curriculum or authorization.
import type {GoalSpec, PlanningDraft, PlanningPlan} from '../../api/client';
export type Fact = Record<string, unknown>;
export function serverGoal(plan:PlanningDraft|PlanningPlan):GoalSpec {
    const profile=fact(plan.v2_content?.profile);
    const unique=(values:string[])=>Array.from(new Set(values.map(value=>value.trim()).filter(Boolean)));
    const starting=unique([plan.goal_spec?.starting_point || '',text(profile.starting_point),...lines(profile.learner_claims)]).join('\n');
    const constraints=unique([...(plan.goal_spec?.constraints || []),...lines(profile.hard_constraints)]);
    if(plan.goal_spec)return {...plan.goal_spec,starting_point:starting,constraints};
    const depth=text(profile.desired_depth),purpose=text(profile.outcome_purpose);
    return {target:plan.goal_snapshot,starting_point:starting,scope:lines(profile.scope),
        constraints,project_context:text(profile.project_context)||null,
        desired_depth:(['unspecified','foundation','applied','deep'].includes(depth)?depth:'unspecified') as GoalSpec['desired_depth'],
        outcome_purpose:(['learn','interview','portfolio','internship','production'].includes(purpose)?purpose:'learn') as GoalSpec['outcome_purpose']};
}
export const fact = (value: unknown): Fact => value && typeof value === 'object' && !Array.isArray(value) ? value as Fact : {};
export const facts = (value: unknown): Fact[] => Array.isArray(value) ? value.map(fact) : [];
export const text = (value: unknown): string => typeof value === 'string' ? value : '';
export const lines = (value: unknown): string[] => Array.isArray(value) ? value.map(item => typeof item === 'string' ? item : text(fact(item).text)).filter(Boolean) : [];
export const resourceTitle = (value: unknown) => { const title = text(value); return !title || /^(resource|material)_[a-f0-9]{32,}$/i.test(title) ? '指定学习教材' : title; };
export const safeUrl = (value: unknown) => { try {
    const url = new URL(text(value));
    return ['https:', 'http:'].includes(url.protocol) ? url.href : undefined;
}
catch {
    return undefined;
} };
export const progressLabel = (phase: string) => ({ outline: '正在组织阶段安排', structure: '正在整理知识与教材', practice: '正在准备实践与成果要求', validation: '正在核对课程完整性', done: '课程整理完成' }[phase] || '正在准备学习计划');
