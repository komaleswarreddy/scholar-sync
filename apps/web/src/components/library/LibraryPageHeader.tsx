'use client';

import { Plus } from 'lucide-react';
import { LibrarySparkline } from './LibrarySparkline';

type LibraryPageHeaderProps = {
  totalNotebooks: number;
  activeThisWeek: number;
  onNewNotebook?: () => void;
};

export function LibraryPageHeader({
  totalNotebooks,
  activeThisWeek,
  onNewNotebook,
}: LibraryPageHeaderProps) {
  return (
    <header className="mb-6">
      <p className="text-[11px] font-semibold tracking-[0.14em] uppercase text-[var(--color-brand-text)] mb-2">
        LIBRARY
      </p>
      <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
        <div>
          <h1 className="text-[28px] sm:text-[32px] font-bold text-[var(--color-home-text)] tracking-tight leading-tight">
            Your notebooks
          </h1>
          <div className="flex items-center gap-2 mt-2 text-[14px] text-[var(--color-home-text-muted)]">
            <span>
              {totalNotebooks} notebooks • {activeThisWeek} active this week
            </span>
            <LibrarySparkline />
          </div>
        </div>
        <button
          type="button"
          onClick={onNewNotebook}
          className="home-btn-primary flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-[14px] font-semibold shadow-sm flex-shrink-0 self-start lg:self-auto"
        >
          <Plus className="w-4 h-4" strokeWidth={2.5} />
          New notebook
        </button>
      </div>
    </header>
  );
}
