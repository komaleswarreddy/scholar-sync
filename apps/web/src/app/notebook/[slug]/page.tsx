'use client';

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useUserContext } from '@/contexts/UserContext';
import { HomeTopNav } from '@/components/home/HomeTopNav';
import { AiDisclaimerFooter } from '@/components/common/AiDisclaimerFooter';
import {
  NotebookWorkspaceHeader,
  NotebookWorkspacePanels,
  NotebookWorkspaceProvider,
} from '@/components/notebook';
import { useNotebookBySlug } from '@/hooks/useNotebooks';
import { NotebookWorkspaceSkeleton } from '@/components/skeleton';

export default function NotebookWorkspacePage() {
  const router = useRouter();
  const params = useParams();
  const { loading, isSignedIn } = useUserContext();
  const slug = typeof params.slug === 'string' ? params.slug : '';
  const { data: notebook, isLoading, isError, error } = useNotebookBySlug(slug);

  useEffect(() => {
    if (!loading && !isSignedIn) {
      router.replace('/sign-in');
    }
  }, [loading, isSignedIn, router]);

  if (loading || isLoading) {
    return <NotebookWorkspaceSkeleton />;
  }

  if (!isSignedIn) {
    return null;
  }

  if (isError || !notebook) {
    return (
      <div className="min-h-screen home-page flex flex-col items-center justify-center gap-3 px-4">
        <p className="text-[var(--color-home-text)] font-semibold">Notebook not found</p>
        <p className="text-[13px] text-[var(--color-home-text-muted)]">
          {error instanceof Error ? error.message : 'This notebook may have been removed.'}
        </p>
        <button type="button" className="profile-btn-primary" onClick={() => router.push('/library')}>
          Back to library
        </button>
      </div>
    );
  }

  return (
    <NotebookWorkspaceProvider
      notebook={{
        id: notebook.id,
        title: notebook.title,
        slug: notebook.slug,
        mode: notebook.mode,
        subject: notebook.subject,
        focus: notebook.focus,
        mastery_percent: notebook.mastery_percent,
        settings: notebook.settings ?? undefined,
      }}
    >
      <div className="h-screen flex flex-col home-page notebook-workspace overflow-hidden">
        <HomeTopNav activeStyle="pill" />
        <div className="notebook-workspace-header-wrap px-3 md:px-5 border-b border-[var(--color-home-border)] bg-white flex-shrink-0">
          <NotebookWorkspaceHeader />
        </div>
        <div className="notebook-workspace-body flex-1 min-h-0 overflow-hidden flex flex-col">
          <NotebookWorkspacePanels />
        </div>
        <AiDisclaimerFooter />
      </div>
    </NotebookWorkspaceProvider>
  );
}
