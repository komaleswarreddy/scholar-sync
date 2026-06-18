'use client';

import type { StudyModule } from '@/lib/study-planner-types';
import { getSubjectTone } from '@/lib/study-planner-utils';

type ModuleCardProps = {
  module: StudyModule;
  planLabel?: string;
  onClick?: () => void;
};

export function ModuleCard({ module, planLabel, onClick }: ModuleCardProps) {
  const tone = getSubjectTone(module.subject);

  return (
    <button
      type="button"
      className={`study-plan-module-card study-plan-module-card--${tone}`}
      onClick={onClick}
    >
      <span className="study-plan-module-card__subject">{module.subject}</span>
      {planLabel ? (
        <span className="study-plan-module-card__plan">{planLabel}</span>
      ) : null}
      <span className="study-plan-module-card__title">{module.title}</span>
    </button>
  );
}
