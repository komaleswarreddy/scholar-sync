import { useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { handleApiError, getUserFriendlyMessage } from '@/lib/error-handler';
import { homeSummaryKeys } from '@/hooks/useHomeSummary';
import { notebookKeys } from '@/hooks/useNotebooks';
import { noteKeys } from '@/hooks/useNotes';
import { tutorCatalogKeys, TUTOR_DEFAULT_CLASS } from '@/hooks/useTutorCatalog';
import { useSessionQueryEnabled } from '@/hooks/usePlatformSession';

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

async function fetchTutorSubjects() {
  try {
    const data = await apiClient.getTutorCatalog({ class_num: TUTOR_DEFAULT_CLASS });
    return data.subjects ?? [];
  } catch (error: unknown) {
    const apiError =
      (error as { apiError?: ReturnType<typeof handleApiError> }).apiError ||
      handleApiError(error);
    throw new Error(getUserFriendlyMessage(apiError));
  }
}

/** Prefetch all student portal queries (call after login or layout mount). */
export function prefetchStudentPortalData(queryClient: ReturnType<typeof useQueryClient>) {
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
  void queryClient.prefetchQuery({
    queryKey: noteKeys.lists(),
    queryFn: fetchNotesList,
    staleTime: 60 * 1000,
  });
  void queryClient.prefetchQuery({
    queryKey: tutorCatalogKeys.subjects(TUTOR_DEFAULT_CLASS),
    queryFn: fetchTutorSubjects,
    staleTime: 60 * 1000,
  });
}

/** Prefetch student portal queries when session token is available. */
export function usePrefetchStudentData() {
  const queryClient = useQueryClient();
  const queryEnabled = useSessionQueryEnabled();

  useEffect(() => {
    if (!queryEnabled) return;
    prefetchStudentPortalData(queryClient);
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
