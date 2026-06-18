'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { handleApiError, getUserFriendlyMessage } from '@/lib/error-handler';
import type { ProblemSolverSession } from '@/types/problem-solver';

export const problemSolverKeys = {
  all: ['problem-solver'] as const,
  active: (notebookId: string) => [...problemSolverKeys.all, 'active', notebookId] as const,
  session: (sessionId: string) => [...problemSolverKeys.all, 'session', sessionId] as const,
};

export function useActiveProblemSolverSession(notebookId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: problemSolverKeys.active(notebookId ?? ''),
    queryFn: async () => {
      if (!notebookId) return null;
      try {
        const data = await apiClient.getActiveProblemSolverSession(notebookId);
        return (data ?? null) as ProblemSolverSession | null;
      } catch (error: unknown) {
        const apiError = handleApiError(error);
        if (apiError.statusCode === 404) return null;
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    enabled: Boolean(notebookId) && enabled,
    staleTime: 0,
  });
}

export function useCreateProblemSolverSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      notebook_id: string;
      problem_text: string;
      input_type?: string;
      source_refs?: Array<Record<string, unknown>>;
    }) => {
      const data = await apiClient.createProblemSolverSession(payload);
      return data as ProblemSolverSession;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(problemSolverKeys.active(data.notebook_id), data);
    },
  });
}

export function useSelectProblemSolverMode() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      sessionId,
      solvingMode,
    }: {
      sessionId: string;
      solvingMode: string;
    }) => {
      const data = await apiClient.selectProblemSolverMode(sessionId, solvingMode);
      return data as ProblemSolverSession;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(problemSolverKeys.active(data.notebook_id), data);
      queryClient.setQueryData(problemSolverKeys.session(data.session_id), data);
    },
  });
}

export function useSubmitProblemSolverCheckpoint() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      sessionId,
      checkpointNumber,
      selectedOption,
    }: {
      sessionId: string;
      checkpointNumber: number;
      selectedOption: string;
    }) => {
      const data = await apiClient.submitProblemSolverCheckpoint(
        sessionId,
        checkpointNumber,
        selectedOption,
      );
      return data as ProblemSolverSession;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(problemSolverKeys.active(data.notebook_id), data);
      queryClient.setQueryData(problemSolverKeys.session(data.session_id), data);
    },
  });
}

export function useProblemSolverFollowUp() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      sessionId,
      action,
      userFollowUp,
    }: {
      sessionId: string;
      action: string;
      userFollowUp?: string;
    }) => {
      return apiClient.triggerProblemSolverFollowUp(sessionId, action, userFollowUp);
    },
    onSuccess: (data, variables) => {
      const session = data as ProblemSolverSession | { redirect?: string };
      if (session && 'session_id' in session && session.session_id) {
        queryClient.setQueryData(problemSolverKeys.active(session.notebook_id), session);
        queryClient.setQueryData(problemSolverKeys.session(session.session_id), session);
      }
      void queryClient.invalidateQueries({
        queryKey: problemSolverKeys.session(variables.sessionId),
      });
    },
  });
}

export function useResetProblemSolverSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (notebookId: string) => {
      return apiClient.resetProblemSolverSession(notebookId);
    },
    onSuccess: (_data, notebookId) => {
      queryClient.setQueryData(problemSolverKeys.active(notebookId), null);
    },
  });
}

export function useExtractProblemSolverFromSource() {
  return useMutation({
    mutationFn: async (sourceId: string) => {
      return apiClient.extractProblemSolverFromSource(sourceId);
    },
  });
}
