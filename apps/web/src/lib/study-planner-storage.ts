'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  INSTITUTE_PACE_MODULES,
  INSTITUTE_WEEK_SCHEDULE,
  SEED_STUDY_PLANS,
} from './study-planner-mock-data';
import type {
  CustomPlanFormState,
  ModuleStatus,
  StudyPlan,
  StudyPlanSubjectId,
} from './study-planner-types';
import { getSubjectById } from './study-planner-mock-data';
import { PLAN_DEMO_TODAY } from './study-planner-utils';

const STORAGE_KEY = 'scholarsync:study-plans:v2';

function mergePlanWithSeed(plan: StudyPlan): StudyPlan {
  const seed = SEED_STUDY_PLANS.find((s) => s.id === plan.id);
  if (!seed) return plan;
  const mergedModules =
    seed.modules?.length && plan.modules?.length
      ? seed.modules.map((seedMod) => {
          const stored = plan.modules?.find((m) => m.id === seedMod.id);
          return stored ? { ...seedMod, status: stored.status } : seedMod;
        })
      : seed.modules ?? plan.modules;
  return {
    ...seed,
    ...plan,
    modules: mergedModules,
    dateRange: plan.dateRange ?? seed.dateRange,
    subjects: plan.subjects ?? seed.subjects,
    modulesComplete: plan.modulesComplete ?? seed.modulesComplete,
    modulesTotal: plan.modulesTotal ?? seed.modulesTotal,
    behindDays: plan.behindDays ?? seed.behindDays,
    currentWeekIndex: plan.currentWeekIndex ?? seed.currentWeekIndex,
    planToday: plan.planToday ?? seed.planToday ?? PLAN_DEMO_TODAY,
  };
}

function migratePlans(plans: StudyPlan[]): StudyPlan[] {
  return plans.map(mergePlanWithSeed);
}

function readPlans(): StudyPlan[] {
  if (typeof window === 'undefined') return SEED_STUDY_PLANS;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return SEED_STUDY_PLANS;
    const parsed = JSON.parse(raw) as StudyPlan[];
    const list = Array.isArray(parsed) && parsed.length > 0 ? parsed : SEED_STUDY_PLANS;
    return migratePlans(list);
  } catch {
    return SEED_STUDY_PLANS;
  }
}

function writePlans(plans: StudyPlan[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(plans));
}

function computeTotalDays(form: CustomPlanFormState): number {
  if (form.timelineMode === 'end_date' && form.endDate) {
    const end = new Date(form.endDate);
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    end.setHours(0, 0, 0, 0);
    const diff = Math.ceil((end.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    return Math.max(diff, 1);
  }
  const value = form.durationValue || 1;
  if (form.durationUnit === 'Days') return value;
  if (form.durationUnit === 'Weeks') return value * 7;
  return value * 30;
}

function buildTodayTasks(form: CustomPlanFormState): StudyPlan['todayTasks'] {
  const tasks: StudyPlan['todayTasks'] = [];
  for (const subjectId of form.selectedSubjects) {
    const chapters = form.selectedChapters[subjectId] ?? [];
    if (chapters.length === 0) continue;
    const subject = getSubjectById(subjectId);
    const firstChapter = chapters[0];
    tasks.push({
      label: `Chapter ${firstChapter}`,
      subject: subject.label,
      chapterNo: firstChapter,
      subjectKey: subject.apiKey,
    });
    if (tasks.length >= 2) break;
  }
  return tasks;
}

export function getPlanById(id: string): StudyPlan | null {
  const plans = readPlans();
  const plan = plans.find((p) => p.id === id);
  return plan ? mergePlanWithSeed(plan) : null;
}

export function updateModuleStatus(
  planId: string,
  moduleId: string,
  status: ModuleStatus,
): StudyPlan | null {
  const plans = readPlans();
  const idx = plans.findIndex((p) => p.id === planId);
  if (idx < 0) return null;

  const plan = mergePlanWithSeed(plans[idx]);
  const modules = (plan.modules ?? []).map((m) =>
    m.id === moduleId ? { ...m, status } : m,
  );
  const modulesComplete = modules.filter((m) => m.status === 'completed').length;
  const updated: StudyPlan = {
    ...plan,
    modules,
    modulesComplete,
    modulesTotal: modules.length,
  };
  const next = [...plans];
  next[idx] = updated;
  writePlans(next);
  return updated;
}

export function updateModuleInStorage(
  planId: string,
  moduleId: string,
  patch: Partial<{ status: ModuleStatus }>,
): StudyPlan | null {
  if (patch.status) {
    return updateModuleStatus(planId, moduleId, patch.status);
  }
  return getPlanById(planId);
}

export function createInstitutePlan(): StudyPlan {
  const firstTwo = INSTITUTE_WEEK_SCHEDULE.slice(0, 2);
  return {
    id: `institute-${Date.now()}`,
    name: 'Institute Pace · Term 2',
    type: 'institute',
    currentDay: 1,
    totalDays: 21,
    progressPercent: 5,
    todayTasks: firstTwo.map((row) => ({
      label: row.topic,
      subject: row.subject,
      chapterNo: row.chapterNo,
      subjectKey: row.subjectKey,
    })),
    createdAt: new Date().toISOString(),
    dateRange: { start: PLAN_DEMO_TODAY, end: '2026-06-21' },
    subjects: ['Physics', 'Chemistry', 'Mathematics', 'Biology'],
    modules: INSTITUTE_PACE_MODULES,
    modulesComplete: 0,
    modulesTotal: INSTITUTE_PACE_MODULES.length,
    behindDays: 0,
    currentWeekIndex: 1,
    planToday: PLAN_DEMO_TODAY,
  };
}

export function createCustomPlan(form: CustomPlanFormState, planName?: string): StudyPlan {
  const totalDays = computeTotalDays(form);
  const subjectLabels = form.selectedSubjects.map((id) => getSubjectById(id).label);
  const name =
    planName ||
    (subjectLabels.length <= 2
      ? subjectLabels.join(' & ') + ' Plan'
      : 'Custom Study Plan');

  return {
    id: `custom-${Date.now()}`,
    name,
    type: 'custom',
    currentDay: 1,
    totalDays,
    progressPercent: Math.round((1 / totalDays) * 100),
    todayTasks: buildTodayTasks(form),
    createdAt: new Date().toISOString(),
    dateRange: { start: PLAN_DEMO_TODAY, end: PLAN_DEMO_TODAY },
    subjects: subjectLabels,
    modules: [],
    modulesComplete: 0,
    modulesTotal: 0,
    behindDays: 0,
    currentWeekIndex: 1,
    planToday: PLAN_DEMO_TODAY,
  };
}

export function getDefaultFormState(): CustomPlanFormState {
  return {
    selectedSubjects: [],
    selectedChapters: {} as Record<StudyPlanSubjectId, number[]>,
    timelineMode: 'duration',
    endDate: '',
    durationValue: 4,
    durationUnit: 'Weeks',
    studyTimeMode: 'per_day',
    hoursPerDay: 1.5,
    daysPerWeek: 5,
  };
}

export function validateCustomPlanForm(form: CustomPlanFormState): {
  valid: boolean;
  message: string;
} {
  if (form.selectedSubjects.length === 0) {
    return { valid: false, message: 'Select at least one subject.' };
  }
  for (const subjectId of form.selectedSubjects) {
    const chapters = form.selectedChapters[subjectId] ?? [];
    if (chapters.length === 0) {
      return {
        valid: false,
        message: 'Pick at least one chapter for each selected subject.',
      };
    }
  }
  if (form.timelineMode === 'end_date') {
    if (!form.endDate) {
      return { valid: false, message: 'Choose a future end date.' };
    }
    const end = new Date(form.endDate);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    end.setHours(0, 0, 0, 0);
    if (end <= today) {
      return { valid: false, message: 'Choose a future end date.' };
    }
  }
  return { valid: true, message: 'Ready to generate.' };
}

export function useStudyPlans() {
  const [plans, setPlans] = useState<StudyPlan[]>(SEED_STUDY_PLANS);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setPlans(readPlans());
    setHydrated(true);
  }, []);

  const addPlan = useCallback((plan: StudyPlan) => {
    setPlans((prev) => {
      const next = [plan, ...prev];
      writePlans(next);
      return next;
    });
  }, []);

  const refreshPlan = useCallback((planId: string) => {
    const updated = getPlanById(planId);
    if (!updated) return;
    setPlans((prev) => prev.map((p) => (p.id === planId ? updated : p)));
  }, []);

  return { plans, hydrated, addPlan, refreshPlan };
}
