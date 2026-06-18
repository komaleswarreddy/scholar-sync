'use client';

import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from 'react';
import { GenerationModal, type ContentType } from '@/components/studio/GenerationModal';
import { determineStudioContentType } from '@/lib/studio-content';
import { normalizeStudioType } from '@/lib/studio-display';

export type PreviewableStudioFeature = {
  id?: string;
  type: string;
  title: string;
  content: unknown;
};

type GenerationCallbacks = {
  onRetry?: () => void | Promise<void>;
  onSave?: () => void | Promise<void>;
};

type StudioPreviewContextValue = {
  openPreview: (feature: PreviewableStudioFeature) => void;
  closePreview: () => void;
  showGeneration: (params: {
    studioType: string;
    title: string;
    sourceCount?: number;
    customInstructions?: string;
    onRetry?: () => void | Promise<void>;
    onSave?: () => void | Promise<void>;
  }) => void;
  setGenerationResult: (params: {
    content: string | object;
    studioType: string;
    title?: string;
  }) => void;
  setGenerationError: (message: string) => void;
  setGenerationLoading: (loading: boolean, studioType?: string) => void;
  closeModal: () => void;
  isOpen: boolean;
};

const StudioPreviewContext = createContext<StudioPreviewContextValue | null>(null);

const initialState = {
  isOpen: false,
  title: 'Generated Content',
  content: null as string | object | null,
  studioType: undefined as string | undefined,
  contentType: 'text' as ContentType,
  loading: false,
  sourceCount: undefined as number | undefined,
  customInstructions: undefined as string | undefined,
  error: null as string | null,
  callbacks: {} as GenerationCallbacks,
};

export function StudioPreviewProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState(initialState);

  const closeModal = useCallback(() => {
    setState(initialState);
  }, []);

  const openPreview = useCallback((feature: PreviewableStudioFeature) => {
    const type = normalizeStudioType(feature.type) ?? feature.type;
    setState({
      isOpen: true,
      title: feature.title,
      content: feature.content as string | object,
      studioType: type,
      contentType: determineStudioContentType(type, feature.content) as ContentType,
      loading: false,
      sourceCount: undefined,
      customInstructions: undefined,
      error: null,
      callbacks: {},
    });
  }, []);

  const showGeneration = useCallback(
    (params: {
      studioType: string;
      title: string;
      sourceCount?: number;
      customInstructions?: string;
      onRetry?: () => void | Promise<void>;
      onSave?: () => void | Promise<void>;
    }) => {
      const type = normalizeStudioType(params.studioType) ?? params.studioType;
      setState({
        isOpen: true,
        title: params.title,
        content: null,
        studioType: type,
        contentType: 'text',
        loading: true,
        sourceCount: params.sourceCount,
        customInstructions: params.customInstructions,
        error: null,
        callbacks: { onRetry: params.onRetry, onSave: params.onSave },
      });
    },
    [],
  );

  const setGenerationResult = useCallback(
    (params: { content: string | object; studioType: string; title?: string }) => {
      const type = normalizeStudioType(params.studioType) ?? params.studioType;
      setState((prev) => ({
        ...prev,
        loading: false,
        content: params.content,
        studioType: type,
        title: params.title ?? prev.title,
        contentType: determineStudioContentType(type, params.content) as ContentType,
        error: null,
      }));
    },
    [],
  );

  const setGenerationError = useCallback((message: string) => {
    setState((prev) => ({
      ...prev,
      loading: false,
      content: null,
      error: message,
    }));
  }, []);

  const setGenerationLoading = useCallback((loading: boolean, studioType?: string) => {
    setState((prev) => ({
      ...prev,
      loading,
      studioType: studioType ?? prev.studioType,
      error: loading ? null : prev.error,
    }));
  }, []);

  const value = useMemo<StudioPreviewContextValue>(
    () => ({
      openPreview,
      closePreview: closeModal,
      showGeneration,
      setGenerationResult,
      setGenerationError,
      setGenerationLoading,
      closeModal,
      isOpen: state.isOpen,
    }),
    [
      openPreview,
      closeModal,
      showGeneration,
      setGenerationResult,
      setGenerationError,
      setGenerationLoading,
      state.isOpen,
    ],
  );

  return (
    <StudioPreviewContext.Provider value={value}>
      {children}
      <GenerationModal
        isOpen={state.isOpen}
        onClose={closeModal}
        onSave={state.callbacks.onSave}
        onRetry={state.callbacks.onRetry}
        title={state.title}
        studioType={state.studioType}
        contentType={state.contentType}
        content={state.content}
        loading={state.loading}
        loadingType={state.loading ? state.studioType : undefined}
        sourceCount={state.sourceCount}
        customInstructions={state.customInstructions}
        error={state.error}
      />
    </StudioPreviewContext.Provider>
  );
}

export function useStudioPreview(): StudioPreviewContextValue {
  const ctx = useContext(StudioPreviewContext);
  if (!ctx) {
    throw new Error('useStudioPreview must be used within StudioPreviewProvider');
  }
  return ctx;
}

export function useStudioPreviewSafe(): StudioPreviewContextValue | null {
  return useContext(StudioPreviewContext);
}
