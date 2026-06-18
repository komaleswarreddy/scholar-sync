'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { useRouter } from 'next/navigation';
import { useNotebookContext } from '@/contexts/NotebookContext';
import { apiClient } from '@/lib/api-client';
import { track } from '@/lib/telemetry';
import {
  useActiveProblemSolverSession,
  useCreateProblemSolverSession,
  useProblemSolverFollowUp,
  useResetProblemSolverSession,
  useSelectProblemSolverMode,
  useSubmitProblemSolverCheckpoint,
} from '@/hooks/useProblemSolver';
import type {
  ProblemSolverFlowStep,
  ProblemSolverModeResponse,
  ProblemSolverSection,
  ProblemSolverSession,
  SolvingMode,
} from '@/types/problem-solver';
import { isValidCheckpoint, applyModeResponseToView } from '@/lib/problem-solver-utils';

type ProblemSolverContextValue = {
  session: ProblemSolverSession | null;
  flowStep: ProblemSolverFlowStep;
  isLoadingSession: boolean;
  streamingSections: ProblemSolverSection[];
  streamTitle: string;
  isStreaming: boolean;
  isFollowUpLoading: boolean;
  streamError: string | null;
  pendingCheckpoint: ProblemSolverModeResponse['checkpoint'] | null;
  followUpButtons: NonNullable<ProblemSolverModeResponse['followUpButtons']>;
  submitProblem: (text: string, inputType?: string, sourceRefs?: Array<Record<string, unknown>>) => Promise<void>;
  selectMode: (mode: SolvingMode) => Promise<void>;
  submitCheckpoint: (checkpointNumber: number, optionId: string) => Promise<void>;
  triggerFollowUp: (action: string, userFollowUp?: string) => Promise<void>;
  resetFlow: () => Promise<void>;
  setExtracting: (value: boolean) => void;
};

const ProblemSolverContext = createContext<ProblemSolverContextValue | null>(null);

function deriveFlowStep(
  session: ProblemSolverSession | null | undefined,
  overrides: {
    isExtracting?: boolean;
    isDnaLoading?: boolean;
    isStreaming?: boolean;
    isFollowUpLoading?: boolean;
    showCheckpoint?: boolean;
    showFollowUp?: boolean;
  },
): ProblemSolverFlowStep {
  if (overrides.isExtracting) return 'extracting';
  if (overrides.isDnaLoading) return 'dna_loading';
  if (overrides.isStreaming) return 'streaming_response';
  if (overrides.showCheckpoint) return 'checkpoint';
  if (overrides.showFollowUp) return 'follow_up';
  if (!session) return 'idle_intake';
  if (session.state === 'extracting') return 'extracting';
  if (session.state === 'dna_ready' && session.problem_dna && !session.solving_mode) {
    return 'mode_select';
  }
  if (
    isValidCheckpoint(session.last_response?.checkpoint) &&
    session.solving_mode === 'HELP_ME_SOLVE_IT'
  ) {
    return 'checkpoint';
  }
  if (session.last_response?.followUpButtons?.length) return 'follow_up';
  if (session.state === 'follow_up') return 'follow_up';
  if (session.last_response) return 'follow_up';
  return 'idle_intake';
}

export function ProblemSolverProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { notebook } = useNotebookContext();
  const notebookId = notebook.id;

  const { data: activeSession, isLoading: isLoadingSession } = useActiveProblemSolverSession(
    notebookId,
  );
  const createSession = useCreateProblemSolverSession();
  const selectModeMutation = useSelectProblemSolverMode();
  const checkpointMutation = useSubmitProblemSolverCheckpoint();
  const followUpMutation = useProblemSolverFollowUp();
  const resetMutation = useResetProblemSolverSession();

  const [localSession, setLocalSession] = useState<ProblemSolverSession | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamTitle, setStreamTitle] = useState('');
  const [streamingSections, setStreamingSections] = useState<ProblemSolverSection[]>([]);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [forceIntake, setForceIntake] = useState(false);

  const session = forceIntake ? null : localSession ?? activeSession ?? null;

  useEffect(() => {
    if (!forceIntake && activeSession && !localSession) {
      setLocalSession(activeSession);
      if (activeSession.last_response?.sections?.length) {
        const { title, sections } = applyModeResponseToView(activeSession.last_response);
        setStreamingSections(sections);
        setStreamTitle(title);
      }
    }
  }, [activeSession, forceIntake, localSession]);

  const pendingCheckpoint = useMemo(() => {
    if (session?.solving_mode !== 'HELP_ME_SOLVE_IT') return null;
    if (session.interaction_count >= 2) return null;
    const checkpoint = session.last_response?.checkpoint;
    return isValidCheckpoint(checkpoint) ? checkpoint : null;
  }, [session]);

  const followUpButtons = session?.last_response?.followUpButtons ?? [];

  const isFollowUpLoading = followUpMutation.isPending;

  const flowStep = deriveFlowStep(session, {
    isExtracting,
    isDnaLoading: createSession.isPending,
    isStreaming,
    isFollowUpLoading,
    showCheckpoint: Boolean(pendingCheckpoint) && !isStreaming,
    showFollowUp:
      Boolean(followUpButtons.length) &&
      !isStreaming &&
      !pendingCheckpoint &&
      Boolean(session?.last_response),
  });

  const runStream = useCallback(async (sessionId: string) => {
    setIsStreaming(true);
    setStreamError(null);
    setStreamingSections([]);
    setStreamTitle('');

    await apiClient.streamProblemSolverResponse(sessionId, {
      onStart: (data) => {
        setStreamTitle(data.title ?? '');
      },
      onSection: (data) => {
        setStreamingSections((prev) => {
          const next = [...prev];
          const idx = data.index ?? next.length;
          next[idx] = {
            heading: data.heading ?? '',
            bodyMarkdown: data.bodyMarkdown ?? '',
          };
          return next;
        });
      },
      onDone: async (data) => {
        setIsStreaming(false);
        const refreshed = (await apiClient.getProblemSolverSession(sessionId)) as ProblemSolverSession;
        setLocalSession(refreshed);
        track('problem_solver.response_complete', {
          session_id: sessionId,
          mode: refreshed.solving_mode,
        });
        if (data.checkpoint) {
          track('problem_solver.checkpoint_shown', { session_id: sessionId });
        }
      },
      onError: (message) => {
        setIsStreaming(false);
        setStreamError(message);
      },
    });
  }, []);

  const submitProblem = useCallback(
    async (
      text: string,
      inputType = 'text',
      sourceRefs?: Array<Record<string, unknown>>,
    ) => {
      setForceIntake(false);
      setStreamError(null);
      const created = await createSession.mutateAsync({
        notebook_id: notebookId,
        problem_text: text,
        input_type: inputType,
        source_refs: sourceRefs,
      });
      setLocalSession(created);
      track('problem_solver.session_created', { notebook_id: notebookId, input_type: inputType });
    },
    [createSession, notebookId],
  );

  const selectMode = useCallback(
    async (mode: SolvingMode) => {
      if (!session) return;
      track('problem_solver.mode_selected', { mode, session_id: session.session_id });
      const updated = await selectModeMutation.mutateAsync({
        sessionId: session.session_id,
        solvingMode: mode,
      });
      setLocalSession(updated);
      await runStream(updated.session_id);
    },
    [runStream, selectModeMutation, session],
  );

  const submitCheckpoint = useCallback(
    async (checkpointNumber: number, optionId: string) => {
      if (!session) return;
      track('problem_solver.checkpoint_submitted', {
        session_id: session.session_id,
        checkpoint_number: checkpointNumber,
      });
      const updated = await checkpointMutation.mutateAsync({
        sessionId: session.session_id,
        checkpointNumber,
        selectedOption: optionId,
      });
      setLocalSession(updated);
      const { title, sections } = applyModeResponseToView(updated.last_response);
      if (sections.length) {
        setStreamingSections(sections);
        setStreamTitle(title);
      }
    },
    [checkpointMutation, session],
  );

  const triggerFollowUp = useCallback(
    async (action: string, userFollowUp?: string) => {
      if (!session) return;
      track('problem_solver.follow_up', { action, session_id: session.session_id });
      setStreamError(null);
      try {
        const result = (await followUpMutation.mutateAsync({
          sessionId: session.session_id,
          action,
          userFollowUp,
        })) as ProblemSolverSession & {
          redirect?: string;
          query?: Record<string, string | number>;
        };
        if (result?.redirect === '/tutor' && result.query) {
          const q = new URLSearchParams();
          Object.entries(result.query as Record<string, string | number>).forEach(([k, v]) => {
            if (v != null && v !== '') q.set(k, String(v));
          });
          router.push(`/tutor?${q.toString()}`);
          return;
        }
        if (result?.session_id) {
          setLocalSession(result);
          const { title, sections } = applyModeResponseToView(result.last_response);
          setStreamingSections(sections);
          setStreamTitle(title);
          if (!sections.length) {
            setStreamError('Follow-up completed but no content was returned. Try another action.');
          }
        }
      } catch (error: unknown) {
        const message =
          error instanceof Error ? error.message : 'Follow-up failed. Please try again.';
        setStreamError(message);
        throw error;
      }
    },
    [followUpMutation, router, session],
  );

  const resetFlow = useCallback(async () => {
    await resetMutation.mutateAsync(notebookId);
    setLocalSession(null);
    setForceIntake(true);
    setStreamingSections([]);
    setStreamTitle('');
    setStreamError(null);
    setIsExtracting(false);
    track('problem_solver.reset', { notebook_id: notebookId });
  }, [notebookId, resetMutation]);

  const value = useMemo<ProblemSolverContextValue>(
    () => ({
      session,
      flowStep,
      isLoadingSession,
      streamingSections,
      streamTitle,
      isStreaming,
      isFollowUpLoading,
      streamError,
      pendingCheckpoint,
      followUpButtons,
      submitProblem,
      selectMode,
      submitCheckpoint,
      triggerFollowUp,
      resetFlow,
      setExtracting: setIsExtracting,
    }),
    [
      session,
      flowStep,
      isLoadingSession,
      streamingSections,
      streamTitle,
      isStreaming,
      isFollowUpLoading,
      streamError,
      pendingCheckpoint,
      followUpButtons,
      submitProblem,
      selectMode,
      submitCheckpoint,
      triggerFollowUp,
      resetFlow,
    ],
  );

  return (
    <ProblemSolverContext.Provider value={value}>{children}</ProblemSolverContext.Provider>
  );
}

export function useProblemSolverContext() {
  const ctx = useContext(ProblemSolverContext);
  if (!ctx) {
    throw new Error('useProblemSolverContext must be used within ProblemSolverProvider');
  }
  return ctx;
}

export function useProblemSolverOptional() {
  return useContext(ProblemSolverContext);
}
