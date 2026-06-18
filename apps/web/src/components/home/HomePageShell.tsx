'use client';

import { ReactNode } from 'react';
import { HomeTopNav } from './HomeTopNav';
import { HomeMobileNav } from './HomeMobileNav';

export function HomePageShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col home-page">
      <HomeTopNav />
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 md:px-8 py-6 md:py-8">
          <HomeMobileNav />
          {children}
        </div>
      </div>
    </div>
  );
}
