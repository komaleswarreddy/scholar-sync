import { Calendar } from 'lucide-react';

type StudyPlanPageHeaderProps = {
  onOpenCalendar?: () => void;
};

export function StudyPlanPageHeader({ onOpenCalendar }: StudyPlanPageHeaderProps) {
  return (
    <header className="study-plan-page-header mb-8">
      <div className="study-plan-page-header__main">
        <h1 className="text-[52px] font-bold text-[var(--sp-text)] leading-[1.1] tracking-tight">
          Study Plan
        </h1>
        <p className="text-[16px] font-medium text-[var(--sp-text-muted)] mt-2">
          Stay on track with your school&apos;s pace, or set your own.
        </p>
      </div>
      {onOpenCalendar ? (
        <div className="study-plan-page-header__actions">
          <button
            type="button"
            className="study-plan-btn-secondary study-plan-btn-secondary--header"
            onClick={onOpenCalendar}
          >
            <Calendar className="w-4 h-4" strokeWidth={2} />
            Calendar
          </button>
        </div>
      ) : null}
    </header>
  );
}
