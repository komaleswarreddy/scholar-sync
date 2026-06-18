'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { notebookKeys } from '@/hooks/useNotebooks';
import { useNotebookContextOptional } from '@/contexts/NotebookContext';

export type TutorSuggestion = { label: string; prompt: string };

export type TutorStudioRecommendation = {
  type: string;
  reason?: string;
  auto_generate?: boolean;
};

export type TutorBootstrapPayload = {
  opening_summary: string;
  suggestions: TutorSuggestion[];
  studio_recommendations: TutorStudioRecommendation[];
  chat_id?: string | null;
  cached?: boolean;
};

type TutorBootstrapContextValue = {
  isTutor: boolean;
  isBootstrapping: boolean;
  isReady: boolean;
  suggestions: TutorSuggestion[];
  studioRecommendations: TutorStudioRecommendation[];
  overviewChatId?: string;
  studioGenerationStarted: boolean;
  runBootstrap: () => Promise<TutorBootstrapPayload | null>;
};

const TutorBootstrapContext = createContext<TutorBootstrapContextValue | null>(null);

function parseBootstrapSettings(settings?: Record<string, unknown> | null) {
  const raw = settings?.tutor_bootstrap;
  if (!raw || typeof raw !== 'object') {
    return {
      completed: false,
      suggestions: [] as TutorSuggestion[],
      studioRecommendations: [] as TutorStudioRecommendation[],
      overviewChatId: undefined as string | undefined,
      studioGenerationStarted: false,
    };
  }
  const bootstrap = raw as Record<string, unknown>;
  const suggestions = Array.isArray(bootstrap.suggestions)
    ? (bootstrap.suggestions as TutorSuggestion[])
    : [];
  const studioRecommendations = Array.isArray(bootstrap.studio_recommendations)
    ? (bootstrap.studio_recommendations as TutorStudioRecommendation[])
    : [];
  return {
    completed: Boolean(bootstrap.completed_at),
    suggestions,
    studioRecommendations,
    overviewChatId: bootstrap.overview_chat_id
      ? String(bootstrap.overview_chat_id)
      : undefined,
    studioGenerationStarted: Boolean(bootstrap.studio_generation_started),
  };
}

export function TutorBootstrapProvider({ children }: { children: ReactNode }) {
  const notebookCtx = useNotebookContextOptional();
  const queryClient = useQueryClient();
  const isTutor = notebookCtx?.notebook.mode === 'tutor';
  const notebookId = notebookCtx?.notebookId;
  const slug = notebookCtx?.notebook.slug;

  const parsed = useMemo(
    () => parseBootstrapSettings(notebookCtx?.notebook.settings ?? null),
    [notebookCtx?.notebook.settings],
  );

  const [isBootstrapping, setIsBootstrapping] = useState(false);
  const [localPayload, setLocalPayload] = useState<TutorBootstrapPayload | null>(null);
  const [bootstrapFailed, setBootstrapFailed] = useState(false);
  const startedRef = useRef(false);
  const completeDispatchedRef = useRef(false);

  const suggestions = localPayload?.suggestions?.length
    ? localPayload.suggestions
    : parsed.suggestions;
  const studioRecommendations = localPayload?.studio_recommendations?.length
    ? localPayload.studio_recommendations
    : parsed.studioRecommendations;
  const overviewChatId = localPayload?.chat_id ?? parsed.overviewChatId;
  const isReady =
    !isTutor || parsed.completed || Boolean(localPayload) || bootstrapFailed;
  const isBootstrappingState = isTutor && !parsed.completed && isBootstrapping;

  const dispatchComplete = useCallback((payload: TutorBootstrapPayload) => {
    window.dispatchEvent(
      new CustomEvent('tutorBootstrapComplete', {
        detail: payload,
      }),
    );
  }, []);

  const runBootstrap = useCallback(async (): Promise<TutorBootstrapPayload | null> => {
    if (!isTutor || !notebookId || isBootstrapping || parsed.completed) return null;
    setIsBootstrapping(true);
    try {
      const result = (await apiClient.bootstrapTutorNotebook(notebookId)) as TutorBootstrapPayload;
      setLocalPayload(result);
      if (slug) {
        await queryClient.invalidateQueries({ queryKey: notebookKeys.detailBySlug(slug) });
      }
      dispatchComplete(result);
      return result;
    } catch (error) {
      console.warn('[TutorBootstrap] failed:', error);
      setBootstrapFailed(true);
      return null;
    } finally {
      setIsBootstrapping(false);
    }
  }, [
    dispatchComplete,
    isBootstrapping,
    isTutor,
    notebookId,
    parsed.completed,
    queryClient,
    slug,
  ]);

  useEffect(() => {
    if (!isTutor || completeDispatchedRef.current) return;

    if (parsed.completed) {
      completeDispatchedRef.current = true;
      dispatchComplete({
        opening_summary: '',
        suggestions: parsed.suggestions,
        studio_recommendations: parsed.studioRecommendations,
        chat_id: parsed.overviewChatId ?? null,
        cached: true,
      });
      return;
    }

    if (parsed.studioGenerationStarted) {
      completeDispatchedRef.current = true;
      return;
    }

    if (startedRef.current) return;
    startedRef.current = true;
    void runBootstrap().then((payload) => {
      if (payload) {
        completeDispatchedRef.current = true;
      }
    });
  }, [dispatchComplete, isTutor, parsed, runBootstrap]);

  const value = useMemo(
    () => ({
      isTutor,
      isBootstrapping: isBootstrappingState,
      isReady,
      suggestions,
      studioRecommendations,
      overviewChatId,
      studioGenerationStarted: parsed.studioGenerationStarted,
      runBootstrap,
    }),
    [
      isBootstrappingState,
      isReady,
      isTutor,
      overviewChatId,
      parsed.studioGenerationStarted,
      runBootstrap,
      studioRecommendations,
      suggestions,
    ],
  );

  return (
    <TutorBootstrapContext.Provider value={value}>{children}</TutorBootstrapContext.Provider>
  );
}

export function useTutorBootstrap() {
  const ctx = useContext(TutorBootstrapContext);
  if (!ctx) {
    throw new Error('useTutorBootstrap must be used within TutorBootstrapProvider');
  }
  return ctx;
}

export function useTutorBootstrapOptional() {
  return useContext(TutorBootstrapContext);
}
