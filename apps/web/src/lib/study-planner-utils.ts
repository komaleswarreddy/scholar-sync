import type { StudyModule, StudyPlan } from './study-planner-types';

/** Demo anchor date matching reference screenshots (Thu Jun 4, 2026). */
export const PLAN_DEMO_TODAY = '2026-06-04';

export function getPlanToday(plan: StudyPlan): string {
  return plan.planToday ?? PLAN_DEMO_TODAY;
}

export function parseISODate(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number);
  return new Date(y, m - 1, d);
}

export function formatISODate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

export function addDays(iso: string, days: number): string {
  const date = parseISODate(iso);
  date.setDate(date.getDate() + days);
  return formatISODate(date);
}

export function startOfWeekWednesday(iso: string): string {
  const date = parseISODate(iso);
  const day = date.getDay();
  const diff = (day + 4) % 7;
  date.setDate(date.getDate() - diff);
  return formatISODate(date);
}

export function getWeekDays(weekStartIso: string): string[] {
  return Array.from({ length: 7 }, (_, i) => addDays(weekStartIso, i));
}

export function getModulesForWeek(modules: StudyModule[], weekStartIso: string): StudyModule[] {
  const weekDays = new Set(getWeekDays(weekStartIso));
  return modules
    .filter((m) => weekDays.has(m.scheduledDate))
    .sort((a, b) => a.scheduledDate.localeCompare(b.scheduledDate));
}

export function getModulesForDate(modules: StudyModule[], iso: string): StudyModule[] {
  return modules.filter((m) => m.scheduledDate === iso);
}

export function formatDateRange(start: string, end: string): string {
  const s = parseISODate(start);
  const e = parseISODate(end);
  const opts: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' };
  const yearOpts: Intl.DateTimeFormatOptions = { ...opts, year: 'numeric' };
  if (s.getFullYear() === e.getFullYear()) {
    return `${s.toLocaleDateString('en-US', opts)} – ${e.toLocaleDateString('en-US', yearOpts)}`;
  }
  return `${s.toLocaleDateString('en-US', yearOpts)} – ${e.toLocaleDateString('en-US', yearOpts)}`;
}

/** Header pill format: "May 28 - Jun 18" */
export function formatPlanDateRange(start: string, end: string): string {
  const s = parseISODate(start);
  const e = parseISODate(end);
  const startStr = s.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  const endStr = e.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  return `${startStr} - ${endStr}`;
}

export function formatModuleDate(iso: string): string {
  return parseISODate(iso).toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });
}

export function formatListDateHeader(iso: string): string {
  return parseISODate(iso)
    .toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })
    .toUpperCase();
}

/** Week schedule day row: "THURSDAY · MAY 30" */
export function formatWeekDayHeader(iso: string): string {
  const date = parseISODate(iso);
  const weekday = date.toLocaleDateString('en-US', { weekday: 'long' }).toUpperCase();
  const monthDay = date
    .toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    .toUpperCase();
  return `${weekday} · ${monthDay}`;
}

/** List schedule date group: "Thursday, May 30" */
export function formatScheduleListDateHeader(iso: string): string {
  return parseISODate(iso).toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
  });
}

export function getWeekIndexForDate(planStart: string, iso: string): number {
  const start = parseISODate(startOfWeekWednesday(planStart));
  const target = parseISODate(startOfWeekWednesday(iso));
  const diffMs = target.getTime() - start.getTime();
  return Math.floor(diffMs / (7 * 24 * 60 * 60 * 1000)) + 1;
}

export function groupModulesByWeek(
  modules: StudyModule[],
  planStart: string,
): { weekIndex: number; weekStart: string; weekEnd: string; modules: StudyModule[] }[] {
  const byWeek = new Map<number, StudyModule[]>();
  for (const mod of modules) {
    const idx = getWeekIndexForDate(planStart, mod.scheduledDate);
    const list = byWeek.get(idx) ?? [];
    list.push(mod);
    byWeek.set(idx, list);
  }
  return Array.from(byWeek.entries())
    .sort(([a], [b]) => a - b)
    .map(([weekIndex, mods]) => {
      const weekStart = startOfWeekWednesday(mods[0].scheduledDate);
      const weekEnd = addDays(weekStart, 6);
      return { weekIndex, weekStart, weekEnd, modules: mods };
    });
}

export function groupModulesByDate(modules: StudyModule[]): Map<string, StudyModule[]> {
  const map = new Map<string, StudyModule[]>();
  for (const mod of [...modules].sort((a, b) => a.scheduledDate.localeCompare(b.scheduledDate))) {
    const list = map.get(mod.scheduledDate) ?? [];
    list.push(mod);
    map.set(mod.scheduledDate, list);
  }
  return map;
}

export type SubjectTone = 'physics' | 'chemistry' | 'mathematics' | 'biology' | 'default';

export function getSubjectTone(subject: string): SubjectTone {
  const s = subject.toLowerCase();
  if (s.includes('physics')) return 'physics';
  if (s.includes('chemistry')) return 'chemistry';
  if (s.includes('math')) return 'mathematics';
  if (s.includes('biology')) return 'biology';
  return 'default';
}

export function enrichPlan(plan: StudyPlan): StudyPlan {
  if (plan.modules?.length) return plan;
  return plan;
}

export type AggregatedModule = {
  module: StudyModule;
  planId: string;
  planName: string;
};

export function aggregatePlanModules(plans: StudyPlan[]): AggregatedModule[] {
  const entries: AggregatedModule[] = [];
  for (const plan of plans) {
    for (const module of plan.modules ?? []) {
      entries.push({
        module,
        planId: plan.id,
        planName: plan.name,
      });
    }
  }
  return entries.sort((a, b) => {
    const dateCmp = a.module.scheduledDate.localeCompare(b.module.scheduledDate);
    if (dateCmp !== 0) return dateCmp;
    const planCmp = a.planName.localeCompare(b.planName);
    if (planCmp !== 0) return planCmp;
    return a.module.title.localeCompare(b.module.title);
  });
}

export function getEarliestPlanStart(plans: StudyPlan[]): string {
  const starts = plans
    .map((p) => p.dateRange?.start)
    .filter((s): s is string => Boolean(s));
  if (starts.length === 0) return PLAN_DEMO_TODAY;
  return starts.sort()[0];
}
