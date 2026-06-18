'use client';

import {
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Circle,
  SkipForward,
} from 'lucide-react';
import type { StudyModule } from '@/lib/study-planner-types';

type BadgeStyle = 'upper' | 'sentence';

type ScheduleModuleCardProps = {
  module: StudyModule;
  todayIso: string;
  layout?: 'card' | 'row';
  badgeStyle?: BadgeStyle;
  onClick: () => void;
};

function StatusBadge({
  module,
  todayIso,
  badgeStyle,
}: {
  module: StudyModule;
  todayIso: string;
  badgeStyle: BadgeStyle;
}) {
  const upper = badgeStyle === 'upper';

  if (module.status === 'skipped') {
    return (
      <span className="study-plan-schedule-badge study-plan-schedule-badge--skipped">
        {upper ? 'SKIPPED' : 'Skipped'}
      </span>
    );
  }
  if (module.status === 'overdue') {
    return (
      <span className="study-plan-schedule-badge study-plan-schedule-badge--overdue">
        {upper ? 'OVERDUE' : 'Overdue'}
      </span>
    );
  }
  if (module.status === 'in_progress') {
    if (!upper && module.scheduledDate === todayIso) {
      return (
        <span className="study-plan-schedule-badge study-plan-schedule-badge--next">Up next</span>
      );
    }
    return (
      <span className="study-plan-schedule-badge study-plan-schedule-badge--progress">
        {upper ? 'IN PROGRESS' : 'In progress'}
      </span>
    );
  }
  if (module.scheduledDate === todayIso && module.status === 'upcoming') {
    return (
      <span className="study-plan-schedule-badge study-plan-schedule-badge--next">Up next</span>
    );
  }
  return null;
}

function StatusIcon({ status }: { status: StudyModule['status'] }) {
  if (status === 'completed') {
    return <CheckCircle2 className="study-plan-schedule-icon study-plan-schedule-icon--done" />;
  }
  if (status === 'overdue') {
    return <AlertCircle className="study-plan-schedule-icon study-plan-schedule-icon--overdue" />;
  }
  if (status === 'skipped') {
    return <SkipForward className="study-plan-schedule-icon study-plan-schedule-icon--skipped" />;
  }
  return <Circle className="study-plan-schedule-icon study-plan-schedule-icon--upcoming" />;
}

export function ScheduleModuleCard({
  module,
  todayIso,
  layout = 'card',
  badgeStyle = 'upper',
  onClick,
}: ScheduleModuleCardProps) {
  const isToday = module.scheduledDate === todayIso;
  const isUpNext =
    isToday && (module.status === 'upcoming' || module.status === 'in_progress');
  const badge = <StatusBadge module={module} todayIso={todayIso} badgeStyle={badgeStyle} />;

  if (layout === 'row') {
    return (
      <button
        type="button"
        className={`study-plan-schedule-row${isUpNext ? ' study-plan-schedule-row--active' : ''}${module.status === 'skipped' ? ' study-plan-schedule-row--skipped' : ''}`}
        onClick={onClick}
      >
        <StatusIcon status={module.status} />
        <div className="study-plan-schedule-row__body">
          <span className="study-plan-schedule-row__title">{module.title}</span>
          <span className="study-plan-schedule-row__meta">{module.subject}</span>
        </div>
        <div className="study-plan-schedule-row__end">
          {badge}
          <ChevronRight className="study-plan-schedule-row__chevron" strokeWidth={2} />
        </div>
      </button>
    );
  }

  const showChevron = module.status === 'upcoming' && !isToday && !badge;

  return (
    <button
      type="button"
      className={`study-plan-schedule-card study-plan-schedule-card--${module.status}${module.status === 'in_progress' ? ' study-plan-schedule-card--active' : ''}${module.status === 'skipped' ? ' study-plan-schedule-card--skipped' : ''}`}
      onClick={onClick}
    >
      <div className="study-plan-schedule-card__top">
        <StatusIcon status={module.status} />
        <div className="study-plan-schedule-card__top-end">
          {badge}
          {showChevron && (
            <ChevronRight className="study-plan-schedule-card__chevron-inline" strokeWidth={2} />
          )}
        </div>
      </div>
      <span className="study-plan-schedule-card__title">{module.title}</span>
      <div className="study-plan-schedule-card__bottom">
        <span className="study-plan-schedule-card__subject">{module.subject}</span>
      </div>
    </button>
  );
}
