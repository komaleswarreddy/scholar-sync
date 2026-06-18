import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { handleApiError, getUserFriendlyMessage } from '@/lib/error-handler';
import { notebookKeys } from '@/hooks/useNotebooks';
import { useClerkQueryEnabled } from '@/hooks/useClerkQueryEnabled';

export interface StudioFeature {
  id: string;
  notebook_id: string;
  type: string;
  title: string;
  content: unknown;
  source_ids?: string[];
  created_at?: string;
  updated_at?: string;
}

export const studioFeatureKeys = {
  all: ['studio-features'] as const,
  lists: () => [...studioFeatureKeys.all, 'list'] as const,
  list: (params?: { notebookId?: string; type?: string; limit?: number }) =>
    [...studioFeatureKeys.lists(), params ?? {}] as const,
};

export function useStudioFeatures(params?: {
  notebookId?: string;
  type?: string;
  limit?: number;
}) {
  const queryEnabled = useClerkQueryEnabled();
  return useQuery({
    queryKey: studioFeatureKeys.list(params),
    queryFn: async () => {
      try {
        const data = await apiClient.listStudioFeatures({
          notebook_id: params?.notebookId,
          type: params?.type,
          limit: params?.limit,
        });
        return (data?.features ?? []) as StudioFeature[];
      } catch (error: unknown) {
        const apiError =
          (error as { apiError?: ReturnType<typeof handleApiError> }).apiError ||
          handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    enabled: queryEnabled,
    staleTime: 30 * 1000,
  });
}

export function useCreateStudioFeature() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      notebook_id: string;
      type: string;
      title: string;
      content: unknown;
      source_ids?: string[];
    }) => {
      try {
        return (await apiClient.createStudioFeature(payload)) as StudioFeature;
      } catch (error: unknown) {
        const apiError =
          (error as { apiError?: ReturnType<typeof handleApiError> }).apiError ||
          handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: studioFeatureKeys.lists() });
      queryClient.invalidateQueries({ queryKey: notebookKeys.all });
    },
  });
}

export function useDeleteStudioFeature() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (featureId: string) => {
      try {
        await apiClient.deleteStudioFeature(featureId);
        return featureId;
      } catch (error: unknown) {
        const apiError =
          (error as { apiError?: ReturnType<typeof handleApiError> }).apiError ||
          handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: studioFeatureKeys.lists() });
      queryClient.invalidateQueries({ queryKey: notebookKeys.all });
    },
  });
}
