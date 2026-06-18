'use client';

import { Suspense, useCallback, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useUser } from '@clerk/nextjs';
import { HomeTopNav } from '@/components/home/HomeTopNav';
import { HomeMobileNav } from '@/components/home/HomeMobileNav';
import {
  AssetsPageHeader,
  AssetsSearchInput,
  AssetsTabToggle,
  NotesPanel,
  StudyAssetsPanel,
  type AssetsTab,
} from '@/components/assets';
import { NOTE_SORT_OPTIONS } from '@/lib/assets-mock-data';
import { StudioPreviewProvider } from '@/contexts/StudioPreviewContext';

function AssetsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isLoaded, isSignedIn } = useUser();
  const [activeTab, setActiveTab] = useState<AssetsTab>('study-assets');
  const [assetSearch, setAssetSearch] = useState('');
  const [noteSearch, setNoteSearch] = useState('');
  const [noteSort, setNoteSort] =
    useState<(typeof NOTE_SORT_OPTIONS)[number]>('Most recent');

  const setTab = useCallback(
    (tab: AssetsTab) => {
      setActiveTab(tab);
      if (tab === 'notes') {
        setAssetSearch('');
      } else {
        setNoteSearch('');
      }
      const params = new URLSearchParams(searchParams.toString());
      if (tab === 'notes') {
        params.set('tab', 'notes');
      } else {
        params.delete('tab');
      }
      const q = params.toString();
      router.replace(q ? `/assets?${q}` : '/assets', { scroll: false });
    },
    [router, searchParams]
  );

  useEffect(() => {
    setActiveTab(searchParams.get('tab') === 'notes' ? 'notes' : 'study-assets');
  }, [searchParams]);

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.replace('/sign-in');
    }
  }, [isLoaded, isSignedIn, router]);

  if (!isLoaded) {
    return (
      <div className="min-h-screen home-page flex items-center justify-center">
        <p className="text-[var(--color-home-text-muted)]">Loading...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col home-page library-page assets-page">
      <HomeTopNav activeStyle="underline" />
      <main className="flex-1 overflow-y-auto">
        <div className="assets-page-inner">
          <HomeMobileNav />
          <AssetsPageHeader />

          <div className="assets-controls-row">
            <AssetsTabToggle active={activeTab} onChange={setTab} />
            <AssetsSearchInput
              value={activeTab === 'study-assets' ? assetSearch : noteSearch}
              onChange={activeTab === 'study-assets' ? setAssetSearch : setNoteSearch}
              placeholder={
                activeTab === 'study-assets' ? 'Search assets...' : 'Search notes...'
              }
              className="assets-controls-search"
            />
          </div>

          {activeTab === 'study-assets' ? (
            <StudyAssetsPanel
              searchInline
              query={assetSearch}
              onQueryChange={setAssetSearch}
              notebookId={searchParams.get('notebook') ?? undefined}
            />
          ) : (
            <NotesPanel sort={noteSort} onSortChange={setNoteSort} query={noteSearch} />
          )}
        </div>
      </main>
    </div>
  );
}

export default function AssetsPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen home-page flex items-center justify-center">
          <p className="text-[var(--color-home-text-muted)]">Loading...</p>
        </div>
      }
    >
      <StudioPreviewProvider>
        <AssetsPageContent />
      </StudioPreviewProvider>
    </Suspense>
  );
}
