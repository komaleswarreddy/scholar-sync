'use client';

import { ReactNode } from 'react';
import { HomeMobileNav } from '@/components/home/HomeMobileNav';

/** Content wrapper only — top nav is provided by `(student)/layout.tsx`. */
export function StudyPlanPageShell({ children }: { children: ReactNode }) {
  return (
    <div className="study-plan-page max-w-7xl mx-auto px-4 md:px-8 pt-8 md:pt-10 pb-12">
      <HomeMobileNav />
      {children}
    </div>
  );
}
