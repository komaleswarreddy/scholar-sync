'use client';

import { useState } from 'react';
import { ChevronRight, ChevronUp, Info } from 'lucide-react';
import type { StudyModule, StudyPlan } from '@/lib/study-planner-types';
import {
  formatDateRange,
  formatWeekDayHeader,
  getPlanToday,
  getWeekDays,
  groupModulesByDate,
  groupModulesByWeek,
} from '@/lib/study-planner-utils';
import { ScheduleModuleCard } from './ScheduleModuleCard';

type PlanWeekScheduleViewProps = {
  plan: StudyPlan;
  onModuleClick: (module: StudyModule) => void;
};

export function PlanWeekScheduleView({ plan, onModuleClick }: PlanWeekScheduleViewProps) {
  const todayIso = getPlanToday(plan);
  const modules = plan.modules ?? [];
  const planStart = plan.dateRange?.start ?? todayIso;
  const weeks = groupModulesByWeek(modules, planStart);
  const currentWeek = plan.currentWeekIndex ?? 1;
  const [collapsed, setCollapsed] = useState<Record<number, boolean>>({});

  const toggleWeek = (weekIndex: number) => {
    setCollapsed((prev) => ({ ...prev, [weekIndex]: !prev[weekIndex] }));
  };

  return (
    <div className="study-plan-week-schedule">
      {weeks.map((week) => {
        const isCurrent = week.weekIndex === currentWeek;
        const isOpen = collapsed[week.weekIndex] !== true;
        const done = week.modules.filter((m) => m.status === 'completed').length;
        const progressPct =
          week.modules.length > 0 ? Math.round((done / week.modules.length) * 100) : 0;
        const weekDays = getWeekDays(week.weekStart);
        const byDate = groupModulesByDate(week.modules);

        return (
          <div
            key={week.weekIndex}
            className={`study-plan-list-week${isCurrent ? ' study-plan-list-week--current' : ''}`}
          >
            <button
              type="button"
              className="study-plan-list-week__header"
              onClick={() => toggleWeek(week.weekIndex)}
            >
              <span className="study-plan-list-week__chevron-box">
                {isOpen ? (
                  <ChevronUp className="study-plan-list-week__chevron-icon" strokeWidth={2.5} />
                ) : (
                  <ChevronRight className="study-plan-list-week__chevron-icon" strokeWidth={2.5} />
                )}
              </span>
              <span className="study-plan-list-week__title">
                Week {week.weekIndex} · {formatDateRange(week.weekStart, week.weekEnd)}
              </span>
              {isCurrent && <span className="study-plan-list-week__pill">This week</span>}
              <div className="study-plan-list-week__progress-wrap">
                <span className="study-plan-list-week__progress-text">
                  {done} of {week.modules.length} done
                </span>
                <div className="study-plan-list-week__progress-bar">
                  <div
                    className="study-plan-list-week__progress-fill"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
              </div>
            </button>

            {isOpen && (
              <div className="study-plan-list-week__body">
                {weekDays.map((dateIso) => {
                  const dateModules = byDate.get(dateIso) ?? [];
                  const isToday = dateIso === todayIso;
                  const hasModules = dateModules.length > 0;

                  if (!isCurrent && !hasModules) return null;

                  return (
                    <div key={dateIso} className="study-plan-list-day">
                      <div className="study-plan-list-day__header">
                        <span>{formatWeekDayHeader(dateIso)}</span>
                        {isToday && <span className="study-plan-list-day__today">Today</span>}
                      </div>

                      {!hasModules ? (
                        <div className="study-plan-list-rest">
                          <Info className="study-plan-list-rest__icon" strokeWidth={2} />
                          <span>Rest day — no modules scheduled.</span>
                        </div>
                      ) : (
                        <div className="study-plan-list-grid">
                          {dateModules.map((mod) => (
                            <ScheduleModuleCard
                              key={mod.id}
                              module={mod}
                              todayIso={todayIso}
                              layout="card"
                              badgeStyle="upper"
                              onClick={() => onModuleClick(mod)}
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
