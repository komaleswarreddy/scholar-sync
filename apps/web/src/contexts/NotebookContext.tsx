'use client';

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

export const DEFAULT_NOTEBOOK_TITLE = 'Untitled notebook';

export interface NotebookRecord {
  id: string;
  title: string;
  slug: string;
  mode: string;
  subject?: string | null;
  focus?: string | null;
  mastery_percent?: number | null;
  settings?: Record<string, unknown> | null;
}

interface NotebookContextValue {
  notebook: NotebookRecord;
  title: string;
  savedTitle: string;
  isTitleDirty: boolean;
  setTitle: (value: string) => void;
  markTitleSaved: (value: string) => void;
  notebookId: string;
}

const NotebookContext = createContext<NotebookContextValue | null>(null);

export function NotebookProvider({
  notebook,
  children,
}: {
  notebook: NotebookRecord;
  children: ReactNode;
}) {
  const [title, setTitleState] = useState(notebook.title);
  const [savedTitle, setSavedTitle] = useState(notebook.title);

  const setTitle = useCallback((value: string) => {
    setTitleState(value);
  }, []);

  const markTitleSaved = useCallback((value: string) => {
    setTitleState(value);
    setSavedTitle(value);
  }, []);

  const value = useMemo(
    () => ({
      notebook,
      title,
      savedTitle,
      isTitleDirty: title.trim() !== savedTitle.trim(),
      setTitle,
      markTitleSaved,
      notebookId: notebook.id,
    }),
    [notebook, title, savedTitle, setTitle, markTitleSaved],
  );

  return <NotebookContext.Provider value={value}>{children}</NotebookContext.Provider>;
}

export function useNotebookContext() {
  const ctx = useContext(NotebookContext);
  if (!ctx) {
    throw new Error('useNotebookContext must be used within NotebookProvider');
  }
  return ctx;
}

export function useNotebookContextOptional() {
  return useContext(NotebookContext);
}

export function useNotebookScopeId(): string | undefined {
  return useContext(NotebookContext)?.notebookId;
}
