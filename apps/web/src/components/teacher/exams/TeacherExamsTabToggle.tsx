'use client';

import type { ExamsListTab } from '@/lib/teacher-exam-types';

interface TeacherExamsTabToggleProps {
  active: ExamsListTab;
  counts: Record<ExamsListTab, number>;
  onChange: (tab: ExamsListTab) => void;
}

const TABS: { id: ExamsListTab; label: string }[] = [
  { id: 'upcoming', label: 'Upcoming' },
  { id: 'graded', label: 'Graded' },
  { id: 'archived', label: 'Archived' },
];

export function TeacherExamsTabToggle({ active, counts, onChange }: TeacherExamsTabToggleProps) {
  return (
    <div className="teacher-exam-tab-toggle" role="tablist" aria-label="Exam categories">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={active === tab.id}
          className={`teacher-exam-tab-toggle__btn${active === tab.id ? ' teacher-exam-tab-toggle__btn--active' : ''}`}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
          <span className="teacher-exam-tab-toggle__count">{counts[tab.id]}</span>
        </button>
      ))}
    </div>
  );
}
