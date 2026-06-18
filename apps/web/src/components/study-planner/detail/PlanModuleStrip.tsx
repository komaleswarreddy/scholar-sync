'use client';

import type { StudyModule } from '@/lib/study-planner-types';
import { ModuleCard } from './ModuleCard';

type PlanModuleStripProps = {
  modules: StudyModule[];
  onModuleClick: (module: StudyModule) => void;
};

export function PlanModuleStrip({ modules, onModuleClick }: PlanModuleStripProps) {
  if (modules.length === 0) return null;

  return (
    <section className="study-plan-module-strip" aria-label="Modules this week">
      <p className="study-plan-module-strip__label">This week&apos;s modules</p>
      <div className="study-plan-module-strip__scroll study-plan-h-scroll">
        {modules.map((mod) => (
          <ModuleCard
            key={mod.id}
            module={mod}
            variant="strip"
            onClick={() => onModuleClick(mod)}
          />
        ))}
      </div>
    </section>
  );
}
