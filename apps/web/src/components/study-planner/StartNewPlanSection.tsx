'use client';

import type { StudyPlan } from '@/lib/study-planner-types';
import { FollowInstituteCard } from './FollowInstituteCard';
import { CustomPlanCard } from './CustomPlanCard';

type StartNewPlanSectionProps = {
  onPlanCreated: (plan: StudyPlan) => void;
  onOpenCustomModal: () => void;
};

export function StartNewPlanSection({
  onPlanCreated,
  onOpenCustomModal,
}: StartNewPlanSectionProps) {
  return (
    <section>
      <h2 className="study-plan-section-label">Start a new plan</h2>
      <p className="study-plan-section-sub">
        Pick how you want the AI to plan your study.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 md:items-stretch">
        <FollowInstituteCard onPlanCreated={onPlanCreated} />
        <div className="flex min-h-0">
          <CustomPlanCard onOpenModal={onOpenCustomModal} />
        </div>
      </div>
      <p className="study-plan-footer-note">
        Plans turn into a sequence of guided study sessions. Click any item in your plan to
        open a tutor session for that topic.
      </p>
    </section>
  );
}
