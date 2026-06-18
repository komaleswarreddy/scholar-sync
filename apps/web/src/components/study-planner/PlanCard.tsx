'use client';

import { useRouter } from 'next/navigation';
import { ChevronRight } from 'lucide-react';
import type { StudyPlan } from '@/lib/study-planner-types';

type PlanCardProps = {
  plan: StudyPlan;
};

export function PlanCard({ plan }: PlanCardProps) {
  const router = useRouter();
  const badgeLabel = plan.type === 'custom' ? 'Custom' : 'Institute';

  const goToDetail = () => {
    router.push(`/study-planner/${plan.id}`);
  };

  const handleContinue = () => {
    goToDetail();
  };

  const handleTaskClick = () => {
    goToDetail();
  };

  return (
    <article className="study-plan-card study-plan-plan-card">
      <div className="flex items-start justify-between gap-3 mb-4">
        <h3 className="text-[18px] font-semibold text-[var(--sp-text)] leading-snug">
          {plan.name}
        </h3>
        <span className="study-plan-badge flex-shrink-0">{badgeLabel}</span>
      </div>

      <div className="study-plan-progress-track mb-2">
        <div
          className="study-plan-progress-fill"
          style={{ width: `${plan.progressPercent}%` }}
        />
      </div>
      <p className="text-[14px] font-medium text-[var(--sp-text-muted)] mb-3">
        Day {plan.currentDay} of {plan.totalDays} · {plan.progressPercent}%
      </p>

      <div className="study-plan-plan-card__today">
        <p className="study-plan-today-label">Today</p>
        <div>
          {plan.todayTasks.map((task, index) => (
            <button
              key={`${task.label}-${index}`}
              type="button"
              className="study-plan-task-row"
              onClick={handleTaskClick}
            >
              <span className="truncate">
                {task.label} · {task.subject}
              </span>
              <ChevronRight className="w-4 h-4 flex-shrink-0 text-[var(--sp-text-muted)]" strokeWidth={1.75} />
            </button>
          ))}
        </div>
      </div>

      <button type="button" className="study-plan-btn-primary" onClick={handleContinue}>
        Continue plan
      </button>
    </article>
  );
}
