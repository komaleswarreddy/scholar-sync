/**
 * Dashboard Wrapper (Client Component)
 * 
 * Client-side wrapper for dashboard layout components.
 * This is needed because Next.js App Router layouts cannot be client components directly.
 */

'use client';

import { Header } from '@/components/layout/Header';
import { SourceList } from '@/components/sources/SourceList';
import { StudioSuite } from '@/components/studio/StudioSuite';
import { NotesSection } from '@/components/notes/NotesSection';
import { SourceProvider } from '@/contexts/SourceContext';

export function DashboardWrapper({ children }: { children: React.ReactNode }) {
  return (
    <SourceProvider>
      <div className="h-screen w-screen flex flex-col overflow-hidden" style={{ backgroundColor: '#131314' }}>
        {/* Top Header Ribbon */}
        <Header />
        
        {/* Main Content Area - Bento Grid */}
        <div className="flex-1 flex gap-4 p-4 overflow-hidden">
          {/* Column 1: Source Management (~20-25%) */}
          <aside className="w-[25%] bg-surface rounded-3xl flex flex-col overflow-hidden border border-border-default">
            <SourceList />
          </aside>
          
          {/* Column 2: Chat Interface (~50%) */}
          <main className="flex-1 flex flex-col bg-surface rounded-3xl overflow-hidden border border-border-default min-w-0">
            {children}
          </main>
          
          {/* Column 3: Studio + Notes (~25%) */}
          <aside className="w-[25%] bg-surface rounded-3xl flex flex-col overflow-hidden border border-border-default">
            {/* Studio Suite (Top) */}
            <div className="flex-1 border-b border-border-default min-h-0">
              <StudioSuite />
            </div>
            
            {/* Notes (Bottom) */}
            <div className="flex-1 min-h-0">
              <NotesSection />
            </div>
          </aside>
        </div>
      </div>
    </SourceProvider>
  );
}


