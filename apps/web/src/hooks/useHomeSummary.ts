import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { handleApiError, getUserFriendlyMessage } from '@/lib/error-handler';
import { useClerkQueryEnabled } from '@/hooks/useClerkQueryEnabled';

export interface HomeSummary {
  overview_metrics: {
    syllabus_percent: number;
    tests_completed: number;
    strong_concepts: number;
    needs_attention: number;
  };
  focus_concept?: {
    subject: string;
    topic: string;
    decay_label: string;
  } | null;
  continue_learning: Array<{
    id: string;
    slug: string;
    title: string;
    subject: string;
    topic: string;
    progress: number;
    lastStudied: string;
  }>;
  performance_line: string;
}

export const homeSummaryKeys = {
  all: ['home-summary'] as const,
};

export function useHomeSummary() {
  const queryEnabled = useClerkQueryEnabled();
  return useQuery({
    queryKey: homeSummaryKeys.all,
    queryFn: async () => {
      try {
        return (await apiClient.getHomeSummary()) as HomeSummary;
      } catch (error: unknown) {
        const apiError =
          (error as { apiError?: ReturnType<typeof handleApiError> }).apiError ||
          handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    enabled: queryEnabled,
    staleTime: 60 * 1000,
  });
}
