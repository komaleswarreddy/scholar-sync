'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { X } from 'lucide-react';
import { TutorNotebookPreparingOverlay } from '@/components/tutor/TutorNotebookPreparingOverlay';
import { TOAST_MIN_VISIBLE_MS, useAppToast } from '@/contexts/AppToastContext';
import { useTutorClass } from '@/contexts/TutorClassContext';
import { notebookKeys } from '@/hooks/useNotebooks';
import { homeSummaryKeys } from '@/hooks/useHomeSummary';
import type { StudyModule, StudyPlan } from '@/lib/study-planner-types';
import { studyModuleToPrepareScope } from '@/lib/study-planner-start-notebook';
import {
  aggregatePlanModules,
  getEarliestPlanStart,
  getWeekIndexForDate,
  PLAN_DEMO_TODAY,
} from '@/lib/study-planner-utils';
import {
  updateModuleInStorage,
  updateModuleStatus,
} from '@/lib/study-planner-storage';
import type { TutorPrepareScope } from '@/lib/tutor-notebook-prepare';
import { ModuleDetailModal } from './detail/ModuleDetailModal';
import { PlanWeekCalendar, computeWeekStart } from './detail/PlanWeekCalendar';

type GlobalStudyPlanCalendarModalProps = {
  isOpen: boolean;
  onClose: () => void;
  plans: StudyPlan[];
};

type SelectedModuleContext = {
  module: StudyModule;
  planId: string;
  planName: string;
};

export function GlobalStudyPlanCalendarModal({
  isOpen,
  onClose,
  plans,
}: GlobalStudyPlanCalendarModalProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { showToast } = useAppToast();
  const { classNum } = useTutorClass();

  const [mounted, setMounted] = useState(false);
  const [calendarWeekOffset, setCalendarWeekOffset] = useState(0);
  const [selected, setSelected] = useState<SelectedModuleContext | null>(null);
  const [prepareScope, setPrepareScope] = useState<TutorPrepareScope | null>(null);
  const [isPreparing, setIsPreparing] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (isOpen) {
      setCalendarWeekOffset(0);
      setSelected(null);
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !selected && !isPreparing) onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isOpen, onClose, selected, isPreparing]);

  const aggregated = useMemo(() => aggregatePlanModules(plans), [plans]);
  const modules = useMemo(() => aggregated.map((e) => e.module), [aggregated]);

  const planLabelByModuleId = useMemo(() => {
    const map: Record<string, string> = {};
    for (const entry of aggregated) {
      map[entry.module.id] = entry.planName;
    }
    return map;
  }, [aggregated]);

  const moduleKeyByModuleId = useMemo(() => {
    const map: Record<string, string> = {};
    for (const entry of aggregated) {
      map[entry.module.id] = `${entry.planId}-${entry.module.id}`;
    }
    return map;
  }, [aggregated]);

  const modulePlanMap = useMemo(() => {
    const map = new Map<string, { planId: string; planName: string }>();
    for (const entry of aggregated) {
      map.set(entry.module.id, { planId: entry.planId, planName: entry.planName });
    }
    return map;
  }, [aggregated]);

  const todayIso = PLAN_DEMO_TODAY;
  const planStart = useMemo(() => getEarliestPlanStart(plans), [plans]);

  const weekStart = useMemo(
    () => computeWeekStart(planStart, todayIso, calendarWeekOffset),
    [planStart, todayIso, calendarWeekOffset],
  );

  const weekIndex = useMemo(
    () => getWeekIndexForDate(planStart, weekStart),
    [planStart, weekStart],
  );

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
      const ctx = modulePlanMap.get(module.id);
      if (ctx) {
        updateModuleStatus(ctx.planId, module.id, 'in_progress');
      }
      setSelected(null);
      const scope = studyModuleToPrepareScope(module, classNum);
      setPrepareScope(scope);
      setIsPreparing(true);
    },
    [classNum, modulePlanMap],
  );

  const handleSkipModule = useCallback(
    (module: StudyModule) => {
      const ctx = modulePlanMap.get(module.id);
      if (ctx) {
        updateModuleInStorage(ctx.planId, module.id, { status: 'skipped' });
      }
      setSelected(null);
    },
    [modulePlanMap],
  );

  const handleModuleClick = useCallback(
    (module: StudyModule) => {
      const ctx = modulePlanMap.get(module.id);
      if (!ctx) return;
      setSelected({
        module,
        planId: ctx.planId,
        planName: ctx.planName,
      });
    },
    [modulePlanMap],
  );

  if (!isOpen || !mounted) return null;

  const showPlanLabels = plans.length > 1;

  return createPortal(
    <>
      <div
        className="assets-modal-backdrop study-plan-page study-plan-calendar-backdrop"
        onClick={(e) => {
          if (e.target === e.currentTarget && !selected) onClose();
        }}
        role="presentation"
      >
        <div
          className="study-plan-calendar-modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="global-calendar-title"
          onClick={(e) => e.stopPropagation()}
        >
          <header className="study-plan-calendar-modal__header">
            <div>
              <h2 id="global-calendar-title" className="study-plan-calendar-modal__title">
                Study calendar
              </h2>
              <p className="study-plan-calendar-modal__subtitle">
                All your plans · {plans.length} {plans.length === 1 ? 'plan' : 'plans'}
              </p>
            </div>
            <button
              type="button"
              className="study-plan-modal-close"
              onClick={onClose}
              aria-label="Close calendar"
            >
              <X className="w-5 h-5" strokeWidth={1.75} />
            </button>
          </header>

          <div className="study-plan-calendar-modal__body">
            <div className="study-plan-detail-calendar-wrap">
              <PlanWeekCalendar
                weekStart={weekStart}
                todayIso={todayIso}
                weekIndex={weekIndex}
                modules={modules}
                onWeekChange={(delta) => setCalendarWeekOffset((o) => o + delta)}
                onModuleClick={handleModuleClick}
                showPlanLabel={showPlanLabels}
                planLabelByModuleId={planLabelByModuleId}
                moduleKeyByModuleId={moduleKeyByModuleId}
              />
            </div>
          </div>
        </div>
      </div>

      <ModuleDetailModal
        module={selected?.module ?? null}
        planName={selected?.planName}
        planHref={selected ? `/study-planner/${selected.planId}` : undefined}
        onClose={() => setSelected(null)}
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
    </>,
    document.body,
  );
}
