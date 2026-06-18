'use client';

import { BookOpen, ListChecks } from 'lucide-react';

const BULLETS = [
  'Pick subjects',
  'Pick chapters',
  'Set timeline',
  'Set time per week',
];

type CustomPlanCardProps = {
  onOpenModal: () => void;
};

export function CustomPlanCard({ onOpenModal }: CustomPlanCardProps) {
  return (
    <article className="study-plan-card study-plan-new-card study-plan-new-card--stretch flex-1 w-full">
      <div className="flex items-start gap-3 mb-4">
        <div className="study-plan-icon-box">
          <ListChecks className="w-5 h-5 text-[#22C55E]" strokeWidth={1.75} />
        </div>
        <div>
          <h3 className="text-[18px] font-semibold text-[var(--sp-text)] mb-4">
            Build your own plan
          </h3>
          <p className="text-[14px] font-medium text-[var(--sp-text-muted)] leading-relaxed">
            Tell us what you want to cover and by when — we&apos;ll lay it out.
          </p>
        </div>
      </div>

      <div className="study-plan-bullet-box">
        {BULLETS.map((item) => (
          <div key={item} className="study-plan-bullet-item">
            {item}
          </div>
        ))}
      </div>

      <button type="button" className="study-plan-btn-secondary" onClick={onOpenModal}>
        <BookOpen className="w-4 h-4" strokeWidth={1.75} />
        Create custom plan
      </button>
    </article>
  );
}
