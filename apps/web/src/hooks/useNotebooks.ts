import { useMutation, useQuery, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { handleApiError, getUserFriendlyMessage } from '@/lib/error-handler';
import { homeSummaryKeys } from '@/hooks/useHomeSummary';
import { useClerkQueryEnabled } from '@/hooks/useClerkQueryEnabled';

export interface Notebook {
  id: string;
  title: string;
  slug: string;
  mode: string;
  subtitle?: string | null;
  subject?: string | null;
  class_level?: string | null;
  focus?: string | null;
  mastery_percent?: number | null;
  sources_count?: number;
  chats_count?: number;
  notes_count?: number;
  study_assets_count?: number;
  quizzes_count?: number;
  settings?: Record<string, unknown> | null;
  last_studied_at?: string | null;
  updated_at?: string | null;
}

export interface NotebookListResponse {
  notebooks: Notebook[];
  total: number;
  active_this_week: number;
}

export const notebookKeys = {
  all: ['notebooks'] as const,
  lists: () => [...notebookKeys.all, 'list'] as const,
  detailBySlug: (slug: string) => [...notebookKeys.all, 'slug', slug] as const,
};

export function useListNotebooks() {
  const queryEnabled = useClerkQueryEnabled();
  return useQuery({
    queryKey: notebookKeys.lists(),
    queryFn: async () => {
      try {
        return (await apiClient.listNotebooks()) as NotebookListResponse;
      } catch (error: unknown) {
        const apiError =
          (error as { apiError?: ReturnType<typeof handleApiError> }).apiError ||
          handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    enabled: queryEnabled,
    staleTime: 5 * 60 * 1000,
    placeholderData: keepPreviousData,
  });
}

export function useNotebookBySlug(slug: string | null) {
  const queryEnabled = useClerkQueryEnabled();
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: notebookKeys.detailBySlug(slug || ''),
    queryFn: async () => {
      if (!slug) return null;
      try {
        return (await apiClient.getNotebookBySlug(slug)) as Notebook;
      } catch (error: any) {
        const apiError = error.apiError || handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    enabled: queryEnabled && !!slug,
    staleTime: 30 * 1000,
    // Seed from the already-fetched notebook list cache (e.g. navigating from /library)
    // so the workspace can mount immediately with the real id/mode instead of waiting
    // on this full detail request (which also computes source/note/quiz counts).
    // Sources/chat/studio panels only need notebook.id + notebook.mode to render and
    // fetch their own data, both of which are already present on the list item; this
    // request still runs in the background to fill in fresh counts/settings.
    placeholderData: () => {
      if (!slug) return undefined;
      const cachedList = queryClient.getQueryData<NotebookListResponse>(notebookKeys.lists());
      return cachedList?.notebooks.find((n) => n.slug === slug);
    },
  });
}

export function useCreateNotebook() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      title?: string;
      mode?: string;
      class_level?: string;
      subject?: string;
      focus?: string;
      settings?: Record<string, unknown>;
    }) => {
      try {
        return (await apiClient.createNotebook(payload)) as Notebook;
      } catch (error: any) {
        const apiError = error.apiError || handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notebookKeys.lists() });
      queryClient.invalidateQueries({ queryKey: homeSummaryKeys.all });
    },
  });
}

export function useUpdateNotebook() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      notebookId,
      title,
      touchLastStudied,
    }: {
      notebookId: string;
      title: string;
      touchLastStudied?: boolean;
    }) => {
      try {
        return await apiClient.updateNotebook(notebookId, {
          title,
          touch_last_studied: touchLastStudied,
        });
      } catch (error: any) {
        const apiError = error.apiError || handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    onSuccess: (data) => {
      if (data?.slug) {
        queryClient.invalidateQueries({ queryKey: notebookKeys.detailBySlug(data.slug) });
      }
      queryClient.invalidateQueries({ queryKey: notebookKeys.lists() });
      queryClient.invalidateQueries({ queryKey: homeSummaryKeys.all });
    },
  });
}
