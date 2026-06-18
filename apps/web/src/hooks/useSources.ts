/**
 * TanStack Query hooks for Sources API
 * 
 * Provides loading states, caching, and optimistic updates for source operations
 */

import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { handleApiError, getUserFriendlyMessage } from '@/lib/error-handler';
import { useClerkQueryEnabled } from '@/hooks/useClerkQueryEnabled';

// Query keys
export const sourceKeys = {
  all: ['sources'] as const,
  lists: () => [...sourceKeys.all, 'list'] as const,
  list: (notebookId?: string) =>
    notebookId ? [...sourceKeys.lists(), notebookId] as const : [...sourceKeys.lists()] as const,
};

// Types
export interface Source {
  id: string;
  title: string;
  file_name: string;
  file_type: string;
  file_size: number;
  upload_date: string;
  status: 'processing' | 'indexed' | 'error' | 'completed' | 'failed';
  chunks_count?: number;
  error_message?: string;
}

/**
 * Hook to fetch all sources
 * Uses keepPreviousData so that a failed background refetch
 * (e.g. DB timeout returns 503) does NOT blank the list.
 */
export function useSources(notebookId?: string) {
  const queryEnabled = useClerkQueryEnabled();
  return useQuery({
    queryKey: sourceKeys.list(notebookId),
    queryFn: async () => {
      try {
        const result = await apiClient.listSources(notebookId);
        return (result || []) as Source[];
      } catch (error: any) {
        const apiError = error.apiError || handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    enabled: queryEnabled,
    staleTime: 5 * 1000,
    // Keep showing previous data while a refetch is in progress
    placeholderData: keepPreviousData,
    // Poll more aggressively while any source is still processing so the UI flips to READY
    // shortly after the background ingestion commits the indexed status.
    refetchInterval: (query) => {
      const sources = (query.state.data as Source[] | undefined) ?? [];
      return sources.some((source) => source.status === 'processing') ? 2 * 1000 : 30 * 1000;
    },
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 8000),
  });
}
/**
 * Hook to upload a source file
 */
export function useUploadSource(notebookId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      file,
      title,
      onProgress,
      pdfPassword,
    }: {
      file: File;
      title?: string;
      onProgress?: (percent: number) => void;
      pdfPassword?: string;
    }) => {
      try {
        const result = await apiClient.uploadSource(
          file,
          title,
          onProgress,
          pdfPassword,
          notebookId,
        );
        return result;
      } catch (error: any) {
        const apiError = error.apiError || handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    onSuccess: () => {
      // Force an immediate refresh after upload so we do not sit on the initial
      // "processing" snapshot until the next polling interval.
      queryClient.invalidateQueries({ queryKey: sourceKeys.lists() });
      queryClient.refetchQueries({ queryKey: sourceKeys.lists(), type: 'active' });
    },
  });
}

/**
 * Hook to delete a source
 */
export function useDeleteSource(notebookId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (sourceId: string) => {
      try {
        await apiClient.deleteSource(sourceId);
        return sourceId;
      } catch (error: any) {
        const apiError = error.apiError || handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    // Optimistic update: remove source from cache immediately
    onMutate: async (sourceId) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: sourceKeys.list(notebookId) });

      // Snapshot the previous value
      const previousSources = queryClient.getQueryData<Source[]>(sourceKeys.list(notebookId));

      // Optimistically update to the new value
      queryClient.setQueryData<Source[]>(sourceKeys.list(notebookId), (old) => {
        return old?.filter((source) => source.id !== sourceId) || [];
      });

      // Return a context object with the snapshotted value
      return { previousSources };
    },
    // If the mutation fails, use the context returned from onMutate to roll back
    onError: (err, sourceId, context) => {
      if (context?.previousSources) {
        queryClient.setQueryData(sourceKeys.list(notebookId), context.previousSources);
      }
    },
    // Always refetch after error or success to ensure consistency
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: sourceKeys.lists() });
    },
  });
}
