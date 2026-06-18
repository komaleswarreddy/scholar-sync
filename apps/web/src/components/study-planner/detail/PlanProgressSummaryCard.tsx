'use client';

import type { StudyPlan } from '@/lib/study-planner-types';

type PlanProgressSummaryCardProps = {
  plan: StudyPlan;
};

export function PlanProgressSummaryCard({ plan }: PlanProgressSummaryCardProps) {
  const modulesComplete = plan.modulesComplete ?? 0;
  const modulesTotal = plan.modulesTotal ?? plan.modules?.length ?? 0;
  const behindDays = plan.behindDays ?? 0;

  return (
    <section className="study-plan-detail-progress-card">
      <div className="study-plan-detail-progress-day">
        <p className="study-plan-detail-progress-day__label">
          Day {plan.currentDay} of {plan.totalDays}
        </p>
        <div className="study-plan-detail-progress-day__bar-row">
          <div className="study-plan-detail-progress-bar">
            <div
              className="study-plan-detail-progress-bar__fill"
              style={{ width: `${plan.progressPercent}%` }}
            />
          </div>
          <span className="study-plan-detail-progress-day__pct">{plan.progressPercent}%</span>
        </div>
      </div>

      <p className="study-plan-detail-progress-modules">
        {modulesComplete} of {modulesTotal} modules complete
      </p>

      {behindDays > 0 && (
        <div className="study-plan-detail-behind">
          <span className="study-plan-detail-behind-dot" />
          Behind by {behindDays} day{behindDays === 1 ? '' : 's'}
        </div>
      )}
    </section>
  );
}
