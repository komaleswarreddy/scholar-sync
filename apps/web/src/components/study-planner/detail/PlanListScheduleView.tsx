'use client';

import { Info } from 'lucide-react';
import type { StudyModule, StudyPlan } from '@/lib/study-planner-types';
import {
  formatScheduleListDateHeader,
  getPlanToday,
  groupModulesByDate,
} from '@/lib/study-planner-utils';
import { ScheduleModuleCard } from './ScheduleModuleCard';

type PlanListScheduleViewProps = {
  plan: StudyPlan;
  onModuleClick: (module: StudyModule) => void;
};

export function PlanListScheduleView({ plan, onModuleClick }: PlanListScheduleViewProps) {
  const todayIso = getPlanToday(plan);
  const modules = plan.modules ?? [];
  const byDate = groupModulesByDate(modules);
  const dates = Array.from(byDate.keys()).sort();

  return (
    <div className="study-plan-schedule-list">
      <div className="study-plan-schedule-list__container">
        {dates.map((dateIso) => {
          const dateModules = byDate.get(dateIso) ?? [];
          const isToday = dateIso === todayIso;

          return (
            <div key={dateIso} className="study-plan-schedule-list__group">
              <div className="study-plan-schedule-list__date-header">
                <span>{formatScheduleListDateHeader(dateIso)}</span>
                {isToday && <span className="study-plan-schedule-list__today">Today</span>}
              </div>
              {dateModules.map((mod) => (
                <ScheduleModuleCard
                  key={mod.id}
                  module={mod}
                  todayIso={todayIso}
                  layout="row"
                  badgeStyle="sentence"
                  onClick={() => onModuleClick(mod)}
                />
              ))}
            </div>
          );
        })}
      </div>

      <p className="study-plan-list-footer">
        <Info className="study-plan-list-footer__icon" strokeWidth={2} />
        Modules in your plan map to guided tutor notebooks. Click any module to study it.
      </p>
    </div>
  );
}
