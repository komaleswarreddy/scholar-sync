'use client';

import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from 'react';
import { useApi } from '@/hooks/useApi';
import { useValidSelectedSourceIds } from '@/hooks/useValidSelectedSourceIds';
import { handleApiError, getUserFriendlyMessage } from '@/lib/error-handler';
import { filterRealSourceIds, buildNcertGlobalApiParams, parseTutorScope } from '@/lib/tutor-ncert-source';
import {
  EXPLORATORY_STUDIO_NO_SOURCES_MESSAGE,
  EXPLORATORY_STUDIO_SELECTION_BLOCKED_MESSAGE,
  notebookModeRequiresUploadedSources,
} from '@/lib/exploratory-studio';
import { useStudioChatBridge } from '@/contexts/StudioChatBridgeContext';
import { useStudioPreview } from '@/contexts/StudioPreviewContext';
import { useNotebookContextOptional } from '@/contexts/NotebookContext';

export type StudioContextMode = 'sources_only' | 'chat_hybrid' | 'selection_only';

export type StudioGenerateParams = {
  taskType: string;
  sourceIds?: string[];
  instructions?: string;
  retrievalFocus?: string;
  contextMode?: StudioContextMode;
  chatTranscript?: string;
  selectionText?: string;
};

const TITLE_BY_TYPE: Record<string, string> = {
  mind_map: 'Mind Map',
  flashcards: 'Flashcards',
  quiz: 'Quiz',
  slide_deck: 'Slide Deck',
};

function formatContent(taskType: string, result: any): string | object | null {
  if (result?.content) {
    const content = result.content;
    if (typeof content === 'string' && !content.trim()) {
      return null;
    }
    if (typeof result === 'object' && result !== null) {
      return {
        task_type: result.task_type || taskType,
        content,
      };
    }
    return content;
  }

  if (result?.data) {
    if (Array.isArray(result.data) && result.data.length === 0) {
      return null;
    }
    if (typeof result.data === 'object' && Object.keys(result.data).length === 0) {
      return null;
    }
    if (result.task_type) {
      return result;
    }
    if (taskType) {
      return { task_type: taskType, ...result };
    }
    return result;
  }

  if (!result || (typeof result === 'string' && !result.trim())) {
    return null;
  }

  if (typeof result === 'object' && !result.task_type && taskType) {
    return { task_type: taskType, ...result };
  }

  return result;
}

function titleForType(type: string): string {
  const t = TITLE_BY_TYPE[type];
  return t ? `Generated ${t}` : 'Generated Content';
}

type StudioGenerationContextValue = {
  generate: (params: StudioGenerateParams) => Promise<void>;
  generating: string | null;
  loading: boolean;
  apiError: string | null;
  errorDetails: ReturnType<typeof useApi>['errorDetails'];
  clearError: () => void;
  validationError: string | null;
  clearValidationError: () => void;
};

const StudioGenerationContext = createContext<StudioGenerationContextValue | null>(null);

export function StudioGenerationProvider({ children }: { children: React.ReactNode }) {
  const { loading, error: apiError, errorDetails, executeRequest, clearError, apiClient } = useApi();
  const { validSelectedIds } = useValidSelectedSourceIds();
  const { chatTranscript, hasChatContext } = useStudioChatBridge();
  const preview = useStudioPreview();
  const notebookCtx = useNotebookContextOptional();

  const [generating, setGenerating] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const clearValidationError = useCallback(() => setValidationError(null), []);

  const handleSave = useCallback(() => {
    preview.closeModal();
  }, [preview]);

  const generate = useCallback(
    async (params: StudioGenerateParams) => {
      const {
        taskType,
        sourceIds: sourceIdsParam,
        instructions = '',
        retrievalFocus,
        contextMode: explicitMode,
        chatTranscript: transcriptParam,
        selectionText,
      } = params;

      const rawSourceIds = sourceIdsParam ?? validSelectedIds;
      const sourceIds = filterRealSourceIds(rawSourceIds);
      const tutorScope =
        notebookCtx?.notebook.mode === 'tutor'
          ? parseTutorScope(notebookCtx.notebook.settings ?? null)
          : null;
      const ncertApiParams = buildNcertGlobalApiParams(tutorScope);
      const hasNcertScope = ncertApiParams != null;
      const requiresUploadedSources = notebookModeRequiresUploadedSources(
        notebookCtx?.notebook.mode,
      );
      let mode: StudioContextMode =
        taskType === 'mind_map' ? 'sources_only' : (explicitMode ?? 'sources_only');

      if (taskType !== 'mind_map' && !explicitMode) {
        if (selectionText != null && selectionText.trim().length >= 15) {
          mode = 'selection_only';
        } else if (hasChatContext && (sourceIds.length > 0 || hasNcertScope)) {
          mode = 'chat_hybrid';
        } else {
          mode = 'sources_only';
        }
      }

      setValidationError(null);

      if (mode === 'selection_only') {
        const st = (selectionText || '').trim();
        if (st.length < 15) {
          setValidationError('Selected text is too short. Highlight at least 15 characters.');
          return;
        }
        if (requiresUploadedSources && sourceIds.length === 0) {
          setValidationError(EXPLORATORY_STUDIO_SELECTION_BLOCKED_MESSAGE);
          return;
        }
      } else if (sourceIds.length === 0 && !hasNcertScope) {
        setValidationError(EXPLORATORY_STUDIO_NO_SOURCES_MESSAGE);
        return;
      }

      if (!navigator.onLine) {
        setValidationError('Network disconnected. Please check your internet connection.');
        return;
      }

      const transcriptForApi =
        mode === 'chat_hybrid' ? (transcriptParam ?? chatTranscript).trim() : undefined;
      if (mode === 'chat_hybrid' && !transcriptForApi) {
        setValidationError(
          'Chat context is empty. Send a message first, or use sources-only generation.',
        );
        return;
      }

      const studioExtras =
        mode === 'sources_only'
          ? ncertApiParams ?? undefined
          : {
              contextMode: mode,
              chatTranscript: mode === 'chat_hybrid' ? transcriptForApi : undefined,
              selectionText: mode === 'selection_only' ? (selectionText || '').trim() : undefined,
              ...(ncertApiParams ?? {}),
            };

      const apiSourceIds = mode === 'selection_only' ? [] : sourceIds;

      const hideCustomInstructions =
        taskType === 'quiz' ||
        taskType === 'mind_map' ||
        taskType === 'flashcards';

      const instructionsForApi =
        taskType === 'mind_map' ? undefined : instructions.trim() || undefined;

      setGenerating(taskType);

      const retryParams: StudioGenerateParams = {
        taskType,
        sourceIds: apiSourceIds,
        instructions: taskType === 'mind_map' ? undefined : instructions,
        retrievalFocus,
        contextMode: mode,
        chatTranscript: taskType === 'mind_map' ? undefined : transcriptParam,
        selectionText: taskType === 'mind_map' ? undefined : selectionText,
      };

      preview.showGeneration({
        studioType: taskType,
        title: titleForType(taskType),
        sourceCount: Math.max(apiSourceIds.length, hasNcertScope ? 1 : 0),
        customInstructions: hideCustomInstructions ? undefined : instructions,
        onRetry: () => generate(retryParams),
        onSave: handleSave,
      });

      try {
        const { data: result, errorMessage } = await executeRequest(() =>
          apiClient.generateStudio(
            taskType as any,
            apiSourceIds,
            instructionsForApi,
            retrievalFocus?.trim() || undefined,
            studioExtras,
          ),
        );

        if (!result) {
          preview.setGenerationError(
            errorMessage || 'No content was generated. Please check the backend logs for details.',
          );
          return;
        }

        const formattedContent = formatContent(taskType, result);

        if (formattedContent === null || formattedContent === undefined) {
          preview.setGenerationError(
            'No content was generated. The model may have been blocked or returned empty content. Please try again.',
          );
          return;
        }

        if (taskType === 'quiz' && formattedContent && typeof formattedContent === 'object') {
          const quizData = (formattedContent as any).data || formattedContent;
          if (!quizData.questions || !Array.isArray(quizData.questions) || quizData.questions.length === 0) {
            preview.setGenerationError('Quiz was generated but has an invalid structure. Please try again.');
            return;
          }
        }

        if (taskType === 'flashcards' && formattedContent && typeof formattedContent === 'object') {
          const flashcardsData = (formattedContent as any).data || formattedContent;
          if (Array.isArray(flashcardsData) && flashcardsData.length === 0) {
            preview.setGenerationError('Flashcards were generated but the list is empty. Please try again.');
            return;
          }
        }

        preview.setGenerationResult({
          content: formattedContent,
          studioType: taskType,
          title: titleForType(taskType),
        });

        window.dispatchEvent(
          new CustomEvent('studioFeatureGenerated', {
            detail: {
              type: taskType,
              title: titleForType(taskType),
              content: formattedContent,
              source_ids: apiSourceIds,
            },
          }),
        );
      } catch (err: any) {
        const apiErr = err.apiError || handleApiError(err);
        preview.setGenerationError(getUserFriendlyMessage(apiErr));
      } finally {
        setGenerating(null);
      }
    },
    [apiClient, chatTranscript, executeRequest, handleSave, hasChatContext, notebookCtx, preview, validSelectedIds],
  );

  const value = useMemo<StudioGenerationContextValue>(
    () => ({
      generate,
      generating,
      loading,
      apiError,
      errorDetails,
      clearError,
      validationError,
      clearValidationError,
    }),
    [generate, generating, loading, apiError, errorDetails, clearError, validationError, clearValidationError],
  );

  return <StudioGenerationContext.Provider value={value}>{children}</StudioGenerationContext.Provider>;
}

export function useStudioGeneration(): StudioGenerationContextValue {
  const ctx = useContext(StudioGenerationContext);
  if (!ctx) {
    throw new Error('useStudioGeneration must be used within StudioGenerationProvider');
  }
  return ctx;
}

export function useStudioGenerationSafe(): StudioGenerationContextValue | null {
  return useContext(StudioGenerationContext);
}
