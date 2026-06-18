'use client';

import Link from 'next/link';
import { ArrowLeft, Building2, Calendar, MoreVertical } from 'lucide-react';
import type { StudyPlan } from '@/lib/study-planner-types';
import { formatPlanDateRange } from '@/lib/study-planner-utils';

type PlanDetailHeaderProps = {
  plan: StudyPlan;
};

export function PlanDetailHeader({ plan }: PlanDetailHeaderProps) {
  const badgeLabel = plan.type === 'custom' ? 'Custom' : 'Institute';
  const dateLabel =
    plan.dateRange?.start && plan.dateRange?.end
      ? formatPlanDateRange(plan.dateRange.start, plan.dateRange.end)
      : `Day ${plan.currentDay} of ${plan.totalDays}`;

  const displaySubjects = (plan.subjects ?? []).filter((s) => s !== 'Biology');

  return (
    <header className="study-plan-detail-header">
      <Link href="/study-planner" className="study-plan-detail-back">
        <ArrowLeft className="study-plan-detail-back__icon" strokeWidth={2} />
        <span>Back to plans</span>
      </Link>

      <div className="study-plan-detail-header__row">
        <div className="study-plan-detail-header__main">
          <h1 className="study-plan-detail-title">{plan.name}</h1>
          <div className="study-plan-detail-pills">
            <span className="study-plan-detail-pill">
              <Building2 className="study-plan-detail-pill__icon" strokeWidth={2} />
              {badgeLabel}
            </span>
            <span className="study-plan-detail-pill">
              <Calendar className="study-plan-detail-pill__icon" strokeWidth={2} />
              {dateLabel}
            </span>
            {displaySubjects.map((subject) => (
              <span key={subject} className="study-plan-detail-pill">
                {subject}
              </span>
            ))}
          </div>
        </div>
        <button type="button" className="study-plan-detail-more" aria-label="More options">
          <MoreVertical className="study-plan-detail-more__icon" strokeWidth={2} />
        </button>
      </div>
    </header>
  );
}
