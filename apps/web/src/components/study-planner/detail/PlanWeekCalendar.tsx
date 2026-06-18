'use client';

import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { StudyModule } from '@/lib/study-planner-types';
import {
  addDays,
  getModulesForDate,
  getWeekDays,
  parseISODate,
  startOfWeekWednesday,
} from '@/lib/study-planner-utils';
import { ModuleCard } from './ModuleCard';

type PlanWeekCalendarProps = {
  weekStart: string;
  todayIso: string;
  weekIndex: number;
  modules: StudyModule[];
  onWeekChange: (delta: number) => void;
  onModuleClick: (module: StudyModule) => void;
  showPlanLabel?: boolean;
  planLabelByModuleId?: Record<string, string>;
  moduleKeyByModuleId?: Record<string, string>;
  weekPillLabel?: string;
};

export function PlanWeekCalendar({
  weekStart,
  todayIso,
  weekIndex,
  modules,
  onWeekChange,
  onModuleClick,
  showPlanLabel = false,
  planLabelByModuleId,
  moduleKeyByModuleId,
  weekPillLabel,
}: PlanWeekCalendarProps) {
  const weekDays = getWeekDays(weekStart);
  const midWeek = parseISODate(addDays(weekStart, 3));
  const monthLabel = midWeek.toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric',
  });

  return (
    <section className="study-plan-week-calendar">
      <div className="study-plan-week-calendar__header">
        <div className="study-plan-week-calendar__month-row">
          <span className="study-plan-week-calendar__month">{monthLabel}</span>
          <div className="study-plan-week-calendar__nav-group">
            <button
              type="button"
              className="study-plan-week-calendar__nav"
              onClick={() => onWeekChange(-1)}
              aria-label="Previous week"
            >
              <ChevronLeft className="study-plan-week-calendar__nav-icon" strokeWidth={2.5} />
            </button>
            <button
              type="button"
              className="study-plan-week-calendar__nav"
              onClick={() => onWeekChange(1)}
              aria-label="Next week"
            >
              <ChevronRight className="study-plan-week-calendar__nav-icon" strokeWidth={2.5} />
            </button>
          </div>
        </div>
        <span className="study-plan-week-calendar__week-pill">
          {weekPillLabel ?? `Week ${weekIndex}`}
        </span>
      </div>

      <div className="study-plan-week-calendar__grid">
        {weekDays.map((dayIso) => {
          const dayModules = getModulesForDate(modules, dayIso);
          const date = parseISODate(dayIso);
          const isToday = dayIso === todayIso;
          const dayName = date.toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase();
          const dayNum = date.getDate();

          return (
            <div key={dayIso} className="study-plan-week-calendar__cell">
              <div className="study-plan-week-calendar__cell-head">
                <span className="study-plan-week-calendar__day-name">{dayName}</span>
                {isToday ? (
                  <span className="study-plan-week-calendar__today">{dayNum}</span>
                ) : (
                  <span className="study-plan-week-calendar__day-num">{dayNum}</span>
                )}
              </div>
              <div className="study-plan-week-calendar__cell-body">
                {dayModules.length === 0 ? (
                  <div className="study-plan-week-calendar__empty">No modules</div>
                ) : (
                  dayModules.map((mod) => (
                    <ModuleCard
                      key={moduleKeyByModuleId?.[mod.id] ?? mod.id}
                      module={mod}
                      planLabel={
                        showPlanLabel ? planLabelByModuleId?.[mod.id] : undefined
                      }
                      onClick={() => onModuleClick(mod)}
                    />
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

export function computeWeekStart(_planStart: string, todayIso: string, offset: number): string {
  const base = startOfWeekWednesday(todayIso);
  return addDays(base, offset * 7);
}
