'use client';

import { CalendarDays, Sparkles } from 'lucide-react';
import { INSTITUTE_WEEK_SCHEDULE } from '@/lib/study-planner-mock-data';
import { createInstitutePlan } from '@/lib/study-planner-storage';
import type { StudyPlan } from '@/lib/study-planner-types';
import { useAppToast } from '@/contexts/AppToastContext';

type FollowInstituteCardProps = {
  onPlanCreated: (plan: StudyPlan) => void;
};

export function FollowInstituteCard({ onPlanCreated }: FollowInstituteCardProps) {
  const { showToast } = useAppToast();

  const handleCreate = () => {
    const plan = createInstitutePlan();
    onPlanCreated(plan);
    showToast('Institute study plan created');
    document.getElementById('your-plans')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <article className="study-plan-card study-plan-new-card">
      <div className="flex items-start gap-3 mb-4">
        <div className="study-plan-icon-box">
          <CalendarDays className="w-5 h-5 text-[var(--sp-primary)]" strokeWidth={1.75} />
        </div>
        <div>
          <h3 className="text-[18px] font-semibold text-[var(--sp-text)] mb-4">
            Follow your institute&apos;s schedule
          </h3>
          <p className="text-[14px] font-medium text-[var(--sp-text-muted)] leading-relaxed">
            We&apos;ll turn your school&apos;s syllabus pace into a daily plan.
          </p>
        </div>
      </div>

      <div className="study-plan-schedule-panel">
        <p className="study-plan-schedule-label">This week at your school</p>
        <div className="flex flex-col gap-2">
          {INSTITUTE_WEEK_SCHEDULE.map((row) => (
            <p key={`${row.subject}-${row.topic}`} className="study-plan-schedule-row">
              <strong>{row.subject}</strong> · {row.topic} ({row.chapterLabel})
            </p>
          ))}
        </div>
        <button type="button" className="study-plan-schedule-link">
          View full schedule &gt;
        </button>
      </div>

      <button
        type="button"
        className="study-plan-btn-primary study-plan-btn-primary--lg"
        onClick={handleCreate}
      >
        <Sparkles className="w-4 h-4" strokeWidth={1.75} />
        Create plan from institute schedule
      </button>
    </article>
  );
}
