import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { SourceQuestionDetail, SourceQuestionListResponse } from '@/types/source-question';

export const sourceQuestionKeys = {
  all: ['source-questions'] as const,
  list: (sourceId: string) => [...sourceQuestionKeys.all, sourceId] as const,
  detail: (sourceId: string, questionId: string) =>
    [...sourceQuestionKeys.list(sourceId), questionId] as const,
};

export function useSourceQuestions(sourceId: string | null, enabled = true) {
  return useQuery<SourceQuestionListResponse>({
    queryKey: sourceId ? sourceQuestionKeys.list(sourceId) : sourceQuestionKeys.all,
    queryFn: () => apiClient.listSourceQuestions(sourceId!),
    enabled: Boolean(sourceId) && enabled,
    staleTime: 10_000,
    refetchInterval: (query) => {
      const data = query.state.data;
      const hasQuestions = (data?.questions?.length ?? 0) > 0;
      if (hasQuestions) return false;
      if (data?.status === 'processing') {
        return 2000;
      }
      return false;
    },
  });
}

export function useSourceQuestionDetail(
  sourceId: string | null,
  questionId: string | null,
  enabled = true,
) {
  return useQuery<SourceQuestionDetail>({
    queryKey:
      sourceId && questionId
        ? sourceQuestionKeys.detail(sourceId, questionId)
        : sourceQuestionKeys.all,
    queryFn: () => apiClient.getSourceQuestion(sourceId!, questionId!),
    enabled: Boolean(sourceId && questionId) && enabled,
  });
}

export function useExtractSourceQuestions(sourceId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (force?: boolean) => apiClient.extractSourceQuestions(sourceId!, force),
    onSuccess: (data) => {
      if (!sourceId) return;
      queryClient.setQueryData<SourceQuestionListResponse>(
        sourceQuestionKeys.list(sourceId),
        (prev) => ({
          ...(prev ?? {
            status: 'idle',
            question_count: 0,
            extraction_version: 0,
            questions: [],
          }),
          ...data,
          questions: data.questions?.length
            ? data.questions
            : prev?.questions?.length
              ? prev.questions
              : [],
        }),
      );
    },
  });
}
