import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNotebookContextOptional } from '@/contexts/NotebookContext';
import { useSources, type Source } from '@/hooks/useSources';
import { useNotebookScopeId } from '@/contexts/NotebookContext';
import { useClerkQueryEnabled } from '@/hooks/useClerkQueryEnabled';
import { apiClient } from '@/lib/api-client';
import {
  buildVirtualNcertSource,
  isVirtualNcertSourceId,
  parseTutorScope,
  type TutorScopeSettings,
} from '@/lib/tutor-ncert-source';

async function resolveTutorScope(scope: TutorScopeSettings): Promise<TutorScopeSettings> {
  const subjectKey = scope.subject_key || scope.subject_slug;
  if (scope.class_num == null || !subjectKey || scope.chapter_no == null) return scope;
  try {
    const data = await apiClient.getTutorCatalog({
      class_num: scope.class_num,
      subject: subjectKey,
    });
    const chapter = (data.chapters ?? []).find((ch) => ch.chapter_no === scope.chapter_no);
    if (!chapter) return scope;
    return {
      ...scope,
      filter_chapter_name: chapter.filter_chapter_name ?? scope.filter_chapter_name,
      chapter_title: chapter.chapter_title ?? chapter.title ?? scope.chapter_title,
      ncert_document_id: chapter.ncert_document_id ?? scope.ncert_document_id,
      chunks_count:
        typeof chapter.chunks_count === 'number'
          ? chapter.chunks_count
          : scope.chunks_count,
    };
  } catch {
    return scope;
  }
}

/**
 * Notebook sources merged with the virtual NCERT row for tutor mode.
 */
export function useCombinedSources(notebookId?: string): {
  sources: Source[];
  /** Sources shown in the UI (excludes virtual NCERT row in tutor mode). */
  displaySources: Source[];
  virtualSource: Source | null;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
} {
  const scopeNotebookId = useNotebookScopeId();
  const resolvedNotebookId = notebookId ?? scopeNotebookId;
  const notebookCtx = useNotebookContextOptional();
  const query = useSources(resolvedNotebookId);
  const tutorScope = parseTutorScope(notebookCtx?.notebook.settings ?? null);
  const queryEnabled = useClerkQueryEnabled();

  const scopeQuery = useQuery({
    queryKey: [
      'tutor-scope-enriched',
      notebookCtx?.notebook.id,
      tutorScope?.class_num,
      tutorScope?.subject_key,
      tutorScope?.chapter_no,
    ],
    queryFn: () => resolveTutorScope(tutorScope as TutorScopeSettings),
    enabled: queryEnabled && Boolean(notebookCtx?.notebook.mode === 'tutor' && tutorScope),
    staleTime: 5 * 60 * 1000,
  });

  const virtualSource = useMemo(() => {
    if (!notebookCtx || notebookCtx.notebook.mode !== 'tutor' || !tutorScope) return null;
    const enriched = scopeQuery.data ?? tutorScope;
    return buildVirtualNcertSource(enriched);
  }, [notebookCtx, tutorScope, scopeQuery.data]);

  const sources = useMemo(() => {
    const apiSources = (query.data ?? []) as Source[];
    if (!virtualSource) return apiSources;
    const withoutDup = apiSources.filter((s) => s.id !== virtualSource.id);
    return [virtualSource, ...withoutDup];
  }, [query.data, virtualSource]);

  const isTutorNotebook = notebookCtx?.notebook.mode === 'tutor';

  const displaySources = useMemo(() => {
    if (!isTutorNotebook) return sources;
    return sources.filter((s) => !isVirtualNcertSourceId(s.id));
  }, [sources, isTutorNotebook]);

  return {
    sources,
    displaySources,
    virtualSource,
    isLoading: query.isLoading || scopeQuery.isLoading,
    isError: query.isError,
    error: (query.error as Error | null) ?? null,
  };
}
