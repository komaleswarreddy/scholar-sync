'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { StudyPlanPageShell } from '@/components/study-planner/StudyPlanPageShell';
import { StudyPlanDetailSkeleton } from '@/components/skeleton';
import { PlanDetailHeader } from '@/components/study-planner/detail/PlanDetailHeader';
import { PlanProgressSummaryCard } from '@/components/study-planner/detail/PlanProgressSummaryCard';
import { PlanScheduleSection } from '@/components/study-planner/detail/PlanScheduleSection';
import { PlanWeekCalendar, computeWeekStart } from '@/components/study-planner/detail/PlanWeekCalendar';
import { ModuleDetailModal } from '@/components/study-planner/detail/ModuleDetailModal';
import { TutorNotebookPreparingOverlay } from '@/components/tutor/TutorNotebookPreparingOverlay';
import { TOAST_MIN_VISIBLE_MS, useAppToast } from '@/contexts/AppToastContext';
import { useTutorClass } from '@/contexts/TutorClassContext';
import { notebookKeys } from '@/hooks/useNotebooks';
import { homeSummaryKeys } from '@/hooks/useHomeSummary';
import type { PlanViewMode, StudyModule, StudyPlan } from '@/lib/study-planner-types';
import { studyModuleToPrepareScope } from '@/lib/study-planner-start-notebook';
import { getPlanToday, getWeekIndexForDate } from '@/lib/study-planner-utils';
import {
  getPlanById,
  updateModuleInStorage,
  updateModuleStatus,
} from '@/lib/study-planner-storage';
import type { TutorPrepareScope } from '@/lib/tutor-notebook-prepare';

export default function StudyPlanDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { showToast } = useAppToast();
  const { classNum } = useTutorClass();

  const planId = typeof params.planId === 'string' ? params.planId : '';

  const [plan, setPlan] = useState<StudyPlan | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [viewMode, setViewMode] = useState<PlanViewMode>('week');
  const [calendarWeekOffset, setCalendarWeekOffset] = useState(0);
  const [selectedModule, setSelectedModule] = useState<StudyModule | null>(null);
  const [prepareScope, setPrepareScope] = useState<TutorPrepareScope | null>(null);
  const [isPreparing, setIsPreparing] = useState(false);

  useEffect(() => {
    if (!planId) return;
    const loaded = getPlanById(planId);
    if (!loaded) {
      router.replace('/study-planner');
      return;
    }
    setPlan(loaded);
    setHydrated(true);
  }, [planId, router]);

  const todayIso = plan ? getPlanToday(plan) : '';
  const planStart = plan?.dateRange?.start ?? todayIso;

  const weekStart = useMemo(() => {
    if (!plan) return todayIso;
    return computeWeekStart(planStart, todayIso, calendarWeekOffset);
  }, [plan, planStart, todayIso, calendarWeekOffset]);

  const weekIndex = useMemo(() => {
    return getWeekIndexForDate(planStart, weekStart);
  }, [planStart, weekStart]);

  const refreshPlan = useCallback(() => {
    const updated = getPlanById(planId);
    if (updated) setPlan(updated);
  }, [planId]);

  const handlePrepareReady = useCallback(
    async ({
      slug,
      partialFailure,
      timedOut,
    }: {
      slug: string;
      partialFailure: boolean;
      timedOut: boolean;
    }) => {
      if (partialFailure || timedOut) {
        await showToast(
          'Some study assets are still generating — retry from Recent Assets if needed.',
          { minVisibleMs: TOAST_MIN_VISIBLE_MS },
        );
      } else {
        await showToast('Notebook ready', { minVisibleMs: TOAST_MIN_VISIBLE_MS });
      }
      setIsPreparing(false);
      setPrepareScope(null);
      await queryClient.invalidateQueries({ queryKey: notebookKeys.lists() });
      await queryClient.invalidateQueries({ queryKey: homeSummaryKeys.all });
      router.push(`/notebook/${slug}`);
    },
    [queryClient, router, showToast],
  );

  const handleStartNotebook = useCallback(
    (module: StudyModule) => {
      setSelectedModule(null);
      updateModuleStatus(planId, module.id, 'in_progress');
      refreshPlan();
      const scope = studyModuleToPrepareScope(module, classNum);
      setPrepareScope(scope);
      setIsPreparing(true);
    },
    [classNum, planId, refreshPlan],
  );

  const handleSkipModule = useCallback(
    (module: StudyModule) => {
      updateModuleInStorage(planId, module.id, { status: 'skipped' });
      refreshPlan();
      setSelectedModule(null);
    },
    [planId, refreshPlan],
  );

  if (!hydrated || !plan) {
    return (
      <StudyPlanPageShell>
        <StudyPlanDetailSkeleton />
      </StudyPlanPageShell>
    );
  }

  return (
    <StudyPlanPageShell>
      <div className="study-plan-detail">
        <PlanDetailHeader plan={plan} />
        <PlanProgressSummaryCard plan={plan} />

        <div className="study-plan-detail-calendar-wrap">
          <PlanWeekCalendar
            weekStart={weekStart}
            todayIso={todayIso}
            weekIndex={weekIndex}
            modules={plan.modules ?? []}
            onWeekChange={(delta) => setCalendarWeekOffset((o) => o + delta)}
            onModuleClick={setSelectedModule}
          />
        </div>

        <PlanScheduleSection
          plan={plan}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          onModuleClick={setSelectedModule}
        />
      </div>

      <ModuleDetailModal
        module={selectedModule}
        onClose={() => setSelectedModule(null)}
        onStartNotebook={handleStartNotebook}
        onSkipModule={handleSkipModule}
      />

      {isPreparing && prepareScope && (
        <TutorNotebookPreparingOverlay
          scope={prepareScope}
          onReady={(payload) => void handlePrepareReady(payload)}
          onHardFail={(message) => {
            void showToast(message, { minVisibleMs: TOAST_MIN_VISIBLE_MS });
            setIsPreparing(false);
            setPrepareScope(null);
          }}
          onCancel={() => {
            setIsPreparing(false);
            setPrepareScope(null);
          }}
        />
      )}
    </StudyPlanPageShell>
  );
}
