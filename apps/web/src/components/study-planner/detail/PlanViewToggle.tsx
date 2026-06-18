'use client';

import type { PlanViewMode } from '@/lib/study-planner-types';

type PlanViewToggleProps = {
  value: PlanViewMode;
  onChange: (mode: PlanViewMode) => void;
};

export function PlanViewToggle({ value, onChange }: PlanViewToggleProps) {
  return (
    <div className="study-plan-detail-view-toggle" role="tablist" aria-label="Plan view">
      <button
        type="button"
        role="tab"
        aria-selected={value === 'week'}
        className={`study-plan-detail-view-toggle__btn${value === 'week' ? ' study-plan-detail-view-toggle__btn--active' : ''}`}
        onClick={() => onChange('week')}
      >
        Week view
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={value === 'list'}
        className={`study-plan-detail-view-toggle__btn${value === 'list' ? ' study-plan-detail-view-toggle__btn--active' : ''}`}
        onClick={() => onChange('list')}
      >
        List view
      </button>
    </div>
  );
}
