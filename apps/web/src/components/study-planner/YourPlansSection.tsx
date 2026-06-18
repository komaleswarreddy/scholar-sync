'use client';

import type { StudyPlan } from '@/lib/study-planner-types';
import { PlanCard } from './PlanCard';

type YourPlansSectionProps = {
  plans: StudyPlan[];
};

export function YourPlansSection({ plans }: YourPlansSectionProps) {
  return (
    <section className="mb-12">
      <h2 className="study-plan-section-label">Your plans</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {plans.map((plan) => (
          <PlanCard key={plan.id} plan={plan} />
        ))}
      </div>
    </section>
  );
}
