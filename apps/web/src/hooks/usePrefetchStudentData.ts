import { useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { handleApiError, getUserFriendlyMessage } from '@/lib/error-handler';
import { homeSummaryKeys } from '@/hooks/useHomeSummary';
import { notebookKeys } from '@/hooks/useNotebooks';
import { noteKeys } from '@/hooks/useNotes';
import { useClerkQueryEnabled } from '@/hooks/useClerkQueryEnabled';

async function fetchHomeSummary() {
  try {
    return await apiClient.getHomeSummary();
  } catch (error: unknown) {
    const apiError =
      (error as { apiError?: ReturnType<typeof handleApiError> }).apiError ||
      handleApiError(error);
    throw new Error(getUserFriendlyMessage(apiError));
  }
}

async function fetchNotebooks() {
  try {
    return await apiClient.listNotebooks();
  } catch (error: unknown) {
    const apiError =
      (error as { apiError?: ReturnType<typeof handleApiError> }).apiError ||
      handleApiError(error);
    throw new Error(getUserFriendlyMessage(apiError));
  }
}

async function fetchNotesList() {
  try {
    return await apiClient.listNotes();
  } catch (error: unknown) {
    const apiError =
      (error as { apiError?: ReturnType<typeof handleApiError> }).apiError ||
      handleApiError(error);
    throw new Error(getUserFriendlyMessage(apiError));
  }
}

/** Prefetch student portal queries when Clerk auth is ready. */
export function usePrefetchStudentData() {
  const queryClient = useQueryClient();
  const queryEnabled = useClerkQueryEnabled();

  useEffect(() => {
    if (!queryEnabled) return;

    void queryClient.prefetchQuery({
      queryKey: homeSummaryKeys.all,
      queryFn: fetchHomeSummary,
      staleTime: 60 * 1000,
    });
    void queryClient.prefetchQuery({
      queryKey: notebookKeys.lists(),
      queryFn: fetchNotebooks,
      staleTime: 5 * 60 * 1000,
    });
  }, [queryClient, queryEnabled]);
}

export function prefetchHomeSummary(queryClient: ReturnType<typeof useQueryClient>) {
  return queryClient.prefetchQuery({
    queryKey: homeSummaryKeys.all,
    queryFn: fetchHomeSummary,
    staleTime: 60 * 1000,
  });
}

export function prefetchNotebooks(queryClient: ReturnType<typeof useQueryClient>) {
  return queryClient.prefetchQuery({
    queryKey: notebookKeys.lists(),
    queryFn: fetchNotebooks,
    staleTime: 5 * 60 * 1000,
  });
}

export function prefetchNotesList(queryClient: ReturnType<typeof useQueryClient>) {
  return queryClient.prefetchQuery({
    queryKey: noteKeys.lists(),
    queryFn: fetchNotesList,
    staleTime: 60 * 1000,
  });
}
