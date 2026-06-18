'use client';

import type { PlanViewMode, StudyModule, StudyPlan } from '@/lib/study-planner-types';
import { PlanListScheduleView } from './PlanListScheduleView';
import { PlanViewToggle } from './PlanViewToggle';
import { PlanWeekScheduleView } from './PlanWeekScheduleView';

type PlanScheduleSectionProps = {
  plan: StudyPlan;
  viewMode: PlanViewMode;
  onViewModeChange: (mode: PlanViewMode) => void;
  onModuleClick: (module: StudyModule) => void;
};

export function PlanScheduleSection({
  plan,
  viewMode,
  onViewModeChange,
  onModuleClick,
}: PlanScheduleSectionProps) {
  return (
    <section className="study-plan-detail-schedule-section">
      <header className="study-plan-detail-schedule-header">
        <h2 className="study-plan-detail-schedule-title">Plan schedule</h2>
        <PlanViewToggle value={viewMode} onChange={onViewModeChange} />
      </header>

      <div className="study-plan-detail-schedule-content">
        {viewMode === 'week' ? (
          <PlanWeekScheduleView plan={plan} onModuleClick={onModuleClick} />
        ) : (
          <PlanListScheduleView plan={plan} onModuleClick={onModuleClick} />
        )}
      </div>
    </section>
  );
}
