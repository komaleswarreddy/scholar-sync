'use client';

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { GenerationModal, ContentType } from '@/components/studio/GenerationModal';
import { useApi } from '@/hooks/useApi';
import { useValidSelectedSourceIds } from '@/hooks/useValidSelectedSourceIds';
import { handleApiError, getUserFriendlyMessage } from '@/lib/error-handler';
import type { StudioReportFormat } from '@/lib/api-client';
import { useStudioChatBridge } from '@/contexts/StudioChatBridgeContext';

export type StudioContextMode = 'sources_only' | 'chat_hybrid' | 'selection_only';

export type StudioGenerateParams = {
  taskType: string;
  sourceIds?: string[];
  instructions?: string;
  retrievalFocus?: string;
  reportFormat?: StudioReportFormat;
  contextMode?: StudioContextMode;
  chatTranscript?: string;
  selectionText?: string;
};

const TITLE_BY_TYPE: Record<string, string> = {
  mind_map: 'Mind Map',
  report: 'Reports',
  flashcards: 'Flashcards',
  quiz: 'Quiz',
  infographic: 'Infographic',
  slide_deck: 'Slide Deck',
};

function determineContentType(taskType: string, result: any): ContentType {
  if (result?.content) {
    if (['mind_map', 'report', 'infographic', 'slide_deck'].includes(taskType)) {
      return 'markdown';
    }
    return 'text';
  }
  if (result?.data) {
    return 'json';
  }
  return 'text';
}

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
        ...(result.infographic_data ? { infographic_data: result.infographic_data } : {}),
        ...(result.summary_bullets ? { summary_bullets: result.summary_bullets } : {}),
        ...(result.image_url ? { image_url: result.image_url } : {}),
        ...(result.image_error ? { image_error: result.image_error } : {}),
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
  const { loading, error: apiError, errorDetails, handleRequest, clearError, apiClient } = useApi();
  const { validSelectedIds, validSelectedCount } = useValidSelectedSourceIds();
  const { chatTranscript, hasChatContext } = useStudioChatBridge();

  const [generating, setGenerating] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const clearValidationError = useCallback(() => setValidationError(null), []);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalContent, setModalContent] = useState<string | object | null>(null);
  const [modalContentType, setModalContentType] = useState<ContentType>('text');
  const [modalTitle, setModalTitle] = useState('Generated Content');
  const [modalError, setModalError] = useState<string | null>(null);
  const [lastGenerationType, setLastGenerationType] = useState<string | null>(null);
  const [lastSourceIds, setLastSourceIds] = useState<string[]>([]);
  const [lastCustomInstructions, setLastCustomInstructions] = useState('');
  const [lastRetrievalFocus, setLastRetrievalFocus] = useState('');
  const [lastReportFormat, setLastReportFormat] = useState<StudioReportFormat | null>(null);
  const [lastStudioExtras, setLastStudioExtras] = useState<{
    contextMode?: StudioContextMode;
    chatTranscript?: string;
    selectionText?: string;
  } | null>(null);
  const [sourceCount, setSourceCount] = useState(0);

  const errorDetailsMessage = (errorDetails as { message?: string } | null | undefined)?.message;

  useEffect(() => {
    if (isModalOpen) {
      if (errorDetails?.message) {
        setModalError(errorDetails.message);
        setModalContent(null);
      } else if (apiError) {
        setModalError(typeof apiError === 'string' ? apiError : 'An error occurred during generation');
        setModalContent(null);
      }
    }
  }, [apiError, errorDetails, isModalOpen]);

  const generate = useCallback(
    async (params: StudioGenerateParams) => {
      const {
        taskType,
        sourceIds: sourceIdsParam,
        instructions = '',
        retrievalFocus,
        reportFormat,
        contextMode: explicitMode,
        chatTranscript: transcriptParam,
        selectionText,
      } = params;

      const sourceIds = sourceIdsParam ?? validSelectedIds;
      let mode: StudioContextMode = explicitMode ?? 'sources_only';
      if (!explicitMode) {
        if (selectionText != null && selectionText.trim().length >= 15) {
          mode = 'selection_only';
        } else if (hasChatContext && sourceIds.length > 0) {
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
      } else if (sourceIds.length === 0) {
        setValidationError('Please select at least one source to generate content');
        return;
      }

      if (mode === 'sources_only' && taskType === 'infographic' && sourceIds.length !== 1) {
        setValidationError(
          'Infographic uses one document at a time. Select exactly one source, then try again.'
        );
        return;
      }
      if (
        mode === 'chat_hybrid' &&
        taskType === 'infographic' &&
        sourceIds.length < 1
      ) {
        setValidationError('Select at least one source for infographic with chat context.');
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
          'Chat context is empty. Send a message first, or use sources-only generation.'
        );
        return;
      }

      const studioExtras =
        mode === 'sources_only'
          ? undefined
          : {
              contextMode: mode,
              chatTranscript: mode === 'chat_hybrid' ? transcriptForApi : undefined,
              selectionText: mode === 'selection_only' ? (selectionText || '').trim() : undefined,
            };

      const apiSourceIds = mode === 'selection_only' ? [] : sourceIds;

      setLastGenerationType(taskType);
      setLastSourceIds(apiSourceIds);
      setLastCustomInstructions(instructions);
      setLastRetrievalFocus(retrievalFocus?.trim() || '');
      setLastReportFormat(taskType === 'report' ? (reportFormat ?? 'integrated') : null);
      setLastStudioExtras(studioExtras ?? null);
      setSourceCount(apiSourceIds.length);

      setGenerating(taskType);
      setModalError(null);
      setIsModalOpen(true);
      setModalTitle(titleForType(taskType));
      setModalContent(null);

      try {
        const result = await handleRequest(() =>
          apiClient.generateStudio(
            taskType as any,
            apiSourceIds,
            instructions.trim() || undefined,
            retrievalFocus?.trim() || undefined,
            taskType === 'report' ? (reportFormat ?? 'integrated') : undefined,
            studioExtras
          )
        );

        await new Promise((r) => setTimeout(r, 50));

        if (errorDetails || apiError) {
          const errorMessage = errorDetailsMessage || apiError || 'An error occurred during generation';
          setModalError(errorMessage);
          setModalContent(null);
        } else if (result) {
          const contentType = determineContentType(taskType, result);
          const formattedContent = formatContent(taskType, result);

          if (formattedContent === null || formattedContent === undefined) {
            const errorMessage =
              errorDetailsMessage ||
              apiError ||
              'No content was generated. The model may have been blocked or returned empty content. Please try again.';
            setModalError(errorMessage);
            setModalContent(null);
            return;
          }

          if (taskType === 'quiz' && formattedContent && typeof formattedContent === 'object') {
            const quizData = (formattedContent as any).data || formattedContent;
            if (!quizData.questions || !Array.isArray(quizData.questions) || quizData.questions.length === 0) {
              setModalError('Quiz was generated but has an invalid structure. Please try again.');
              setModalContent(null);
              return;
            }
          }

          if (taskType === 'flashcards' && formattedContent && typeof formattedContent === 'object') {
            const flashcardsData = (formattedContent as any).data || formattedContent;
            if (Array.isArray(flashcardsData) && flashcardsData.length === 0) {
              setModalError('Flashcards were generated but the list is empty. Please try again.');
              setModalContent(null);
              return;
            }
          }

          setModalContentType(contentType);
          setModalContent(formattedContent);
          setModalError(null);

          window.dispatchEvent(
            new CustomEvent('studioFeatureGenerated', {
              detail: {
                type: taskType,
                title: titleForType(taskType),
                content: formattedContent,
              },
            })
          );
        } else {
          const errorMessage =
            errorDetailsMessage ||
            apiError ||
            'No content was generated. Please check the backend logs for details.';
          setModalError(errorMessage);
          setModalContent(null);
        }
      } catch (err: any) {
        const apiErr = err.apiError || handleApiError(err);
        const errorMessage = getUserFriendlyMessage(apiErr);
        setModalError(errorMessage);
        setModalContent(null);
      } finally {
        setGenerating(null);
      }
    },
    [
      apiClient,
      apiError,
      chatTranscript,
      errorDetails,
      errorDetailsMessage,
      handleRequest,
      hasChatContext,
      validSelectedIds,
    ]
  );

  const handleSave = useCallback(() => {
    setIsModalOpen(false);
    setModalContent(null);
    setModalError(null);
  }, []);

  const handleRetry = useCallback(async () => {
    if (!lastGenerationType) return;
    await generate({
      taskType: lastGenerationType,
      sourceIds: lastSourceIds,
      instructions: lastCustomInstructions,
      retrievalFocus: lastRetrievalFocus.trim() || undefined,
      reportFormat: lastGenerationType === 'report' ? (lastReportFormat ?? 'integrated') : undefined,
      contextMode: lastStudioExtras?.contextMode,
      chatTranscript: lastStudioExtras?.chatTranscript,
      selectionText: lastStudioExtras?.selectionText,
    });
  }, [
    generate,
    lastCustomInstructions,
    lastGenerationType,
    lastReportFormat,
    lastRetrievalFocus,
    lastSourceIds,
    lastStudioExtras,
  ]);

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
    [
      generate,
      generating,
      loading,
      apiError,
      errorDetails,
      clearError,
      validationError,
      clearValidationError,
    ]
  );

  return (
    <StudioGenerationContext.Provider value={value}>
      {children}
      <GenerationModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={handleSave}
        onRetry={handleRetry}
        title={modalTitle}
        contentType={modalContentType}
        content={modalContent}
        loading={generating !== null}
        loadingType={generating || undefined}
        sourceCount={sourceCount}
        customInstructions={
          lastGenerationType === 'quiz' ||
          lastGenerationType === 'mind_map' ||
          lastGenerationType === 'report' ||
          lastGenerationType === 'flashcards'
            ? undefined
            : lastCustomInstructions
        }
        error={modalError}
      />
    </StudioGenerationContext.Provider>
  );
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
