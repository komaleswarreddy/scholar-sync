'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@clerk/nextjs';
import { HomeMobileNav } from '@/components/home/HomeMobileNav';
import {
  LibraryBottomBanner,
  LibraryPageHeader,
  LibrarySearchFilters,
  NotebookCard,
} from '@/components/library';
import { LibraryGridSkeleton } from '@/components/skeleton';
import { useListNotebooks } from '@/hooks/useNotebooks';
import { mapApiNotebookToLibrary } from '@/lib/library-mapper';
import type { LibraryNotebook } from '@/lib/library-mock-data';

export default function LibraryPage() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useUser();
  const { data, isLoading, isError } = useListNotebooks();
  const sourceNotebooks = useMemo(
    () => (data?.notebooks ?? []).map(mapApiNotebookToLibrary),
    [data?.notebooks],
  );
  const [notebooks, setNotebooks] = useState<LibraryNotebook[]>([]);

  const handleFiltered = useCallback((list: LibraryNotebook[]) => {
    setNotebooks(list);
  }, []);

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.replace('/sign-in');
    }
  }, [isLoaded, isSignedIn, router]);

  return (
    <div className="library-page max-w-7xl mx-auto px-4 md:px-8 pt-8 md:pt-10 pb-10">
      <HomeMobileNav />
      <LibraryPageHeader
        totalNotebooks={data?.total ?? 0}
        activeThisWeek={data?.active_this_week ?? 0}
        onNewNotebook={() => router.push('/dashboard')}
      />
      {isLoading && !data ? (
        <LibraryGridSkeleton />
      ) : isError ? (
        <p className="text-[var(--color-home-text-muted)] py-8 text-center">
          Could not load notebooks. Please try again.
        </p>
      ) : (
        <>
          <LibrarySearchFilters notebooks={sourceNotebooks} onFilteredChange={handleFiltered} />
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {notebooks.map((notebook) => (
              <NotebookCard
                key={notebook.notebookId ?? notebook.id}
                notebook={notebook}
                onOpen={() => router.push(`/notebook/${notebook.slug ?? notebook.id}`)}
              />
            ))}
          </div>
          {sourceNotebooks.length === 0 && (
            <p className="text-center text-[var(--color-home-text-muted)] py-12 text-[15px]">
              No notebooks yet. Create one from Home to get started.
            </p>
          )}
          {sourceNotebooks.length > 0 && notebooks.length === 0 && (
            <p className="text-center text-[var(--color-home-text-muted)] py-12 text-[15px]">
              No notebooks match your filters.
            </p>
          )}
        </>
      )}
      <LibraryBottomBanner />
    </div>
  );
}
