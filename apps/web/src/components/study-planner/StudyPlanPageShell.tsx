'use client';

import { ReactNode } from 'react';
import { HomeTopNav } from '@/components/home/HomeTopNav';
import { HomeMobileNav } from '@/components/home/HomeMobileNav';

export function StudyPlanPageShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col home-page study-plan-page">
      <HomeTopNav activeStyle="underline" hideClassPill />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-4 md:px-8 pt-8 md:pt-10 pb-12">
          <HomeMobileNav />
          {children}
        </div>
      </main>
    </div>
  );
}
