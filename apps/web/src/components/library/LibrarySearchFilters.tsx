'use client';

import { useEffect, useMemo, useState } from 'react';
import { ChevronDown, Search, SlidersHorizontal } from 'lucide-react';
import { FilterPill } from '@/components/common/FilterPill';
import {
  LIBRARY_CLASS_FILTERS,
  LIBRARY_SORT_OPTIONS,
  LIBRARY_SUBJECT_FILTERS,
  type LibraryNotebook,
} from '@/lib/library-mock-data';

type LibrarySearchFiltersProps = {
  notebooks: LibraryNotebook[];
  onFilteredChange: (notebooks: LibraryNotebook[]) => void;
};

export function LibrarySearchFilters({
  notebooks,
  onFilteredChange,
}: LibrarySearchFiltersProps) {
  const [query, setQuery] = useState('');
  const [subject, setSubject] = useState<(typeof LIBRARY_SUBJECT_FILTERS)[number]>('All');
  const [classFilter, setClassFilter] = useState<(typeof LIBRARY_CLASS_FILTERS)[number]>('All');
  const [sort, setSort] = useState<(typeof LIBRARY_SORT_OPTIONS)[number]>('Recently used');
  const [sortOpen, setSortOpen] = useState(false);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    let list = [...notebooks];

    if (subject !== 'All') {
      list = list.filter((n) => n.subject === subject);
    }
    if (classFilter !== 'All') {
      list = list.filter((n) => n.classLevel === classFilter);
    }
    if (q) {
      list = list.filter((n) => {
        const haystack = [
          n.title,
          n.subtitle,
          n.subject,
          n.classLevel,
          n.focus,
          String(n.sources),
          String(n.studyAssets),
          String(n.quizzes),
        ]
          .join(' ')
          .toLowerCase();
        return haystack.includes(q);
      });
    }

    if (sort === 'Name A–Z') {
      list.sort((a, b) => a.title.localeCompare(b.title));
    } else if (sort === 'Mastery %') {
      list.sort((a, b) => b.masteryPercent - a.masteryPercent);
    } else if (sort === 'Last studied') {
      list.sort((a, b) => {
        const aTime = a.lastStudiedAt ? new Date(a.lastStudiedAt).getTime() : 0;
        const bTime = b.lastStudiedAt ? new Date(b.lastStudiedAt).getTime() : 0;
        return bTime - aTime;
      });
    } else {
      list.sort((a, b) => {
        const aTime = a.lastStudiedAt ? new Date(a.lastStudiedAt).getTime() : 0;
        const bTime = b.lastStudiedAt ? new Date(b.lastStudiedAt).getTime() : 0;
        return bTime - aTime;
      });
    }

    return list;
  }, [query, subject, classFilter, sort, notebooks]);

  useEffect(() => {
    onFilteredChange(filtered);
  }, [filtered, onFilteredChange]);

  return (
    <div className="mb-6 space-y-4">
      <div className="flex flex-col xl:flex-row xl:items-start gap-4">
        <div className="flex-1 min-w-0">
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-home-label)]" />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search notebooks..."
              className="library-search-input w-full pl-10 pr-4 py-2.5 text-[14px]"
            />
          </div>
          <p className="text-[11px] text-[var(--color-home-label)] mt-1.5 pl-0.5">
            Searches in title, subject, chapter, focus, sources &amp; study assets
          </p>
        </div>

        <div className="relative flex-shrink-0">
          <button
            type="button"
            onClick={() => setSortOpen((o) => !o)}
            className="library-sort-btn flex items-center gap-2 px-4 py-2.5 text-[14px] font-medium whitespace-nowrap"
          >
            <SlidersHorizontal className="w-4 h-4 text-[var(--color-home-text-muted)]" />
            {sort}
            <ChevronDown className="w-4 h-4 text-[var(--color-home-label)]" />
          </button>
          {sortOpen && (
            <>
              <div
                className="fixed inset-0 z-10"
                aria-hidden
                onClick={() => setSortOpen(false)}
              />
              <ul className="absolute right-0 top-full mt-1 z-20 min-w-[180px] py-1 bg-white border border-[var(--color-home-border)] rounded-xl shadow-lg">
                {LIBRARY_SORT_OPTIONS.map((opt) => (
                  <li key={opt}>
                    <button
                      type="button"
                      onClick={() => {
                        setSort(opt);
                        setSortOpen(false);
                      }}
                      className={`w-full text-left px-4 py-2 text-[14px] hover:bg-[var(--color-brand-surface)] ${
                        sort === opt
                          ? 'text-[var(--color-brand-text)] font-semibold'
                          : 'text-[var(--color-home-text)]'
                      }`}
                    >
                      {opt}
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>

      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3 lg:gap-6">
        <div className="flex items-center gap-2 flex-wrap">
          {LIBRARY_CLASS_FILTERS.map((label) => (
            <FilterPill
              key={label}
              label={label}
              active={classFilter === label}
              onClick={() => setClassFilter(label)}
            />
          ))}
        </div>
        <div className="flex items-center gap-2 flex-wrap lg:justify-end">
          {LIBRARY_SUBJECT_FILTERS.map((label) => (
            <FilterPill
              key={label}
              label={label}
              active={subject === label}
              onClick={() => setSubject(label)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
