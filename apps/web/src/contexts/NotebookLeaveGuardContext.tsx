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
import {
  DEFAULT_NOTEBOOK_TITLE,
  useNotebookContext,
} from '@/contexts/NotebookContext';
import { TOAST_MIN_VISIBLE_MS, useAppToast } from '@/contexts/AppToastContext';
import { useUpdateNotebook } from '@/hooks/useNotebooks';
import { NotebookSaveNameDialog } from '@/components/notebook/NotebookSaveNameDialog';

type NotebookLeaveGuardContextValue = {
  tryNavigate: (href: string) => void;
  needsLeavePrompt: () => boolean;
};

const NotebookLeaveGuardContext = createContext<NotebookLeaveGuardContextValue | null>(
  null,
);

export function NotebookLeaveGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { showToast } = useAppToast();
  const { notebook, title, setTitle, markTitleSaved } = useNotebookContext();
  const updateNotebook = useUpdateNotebook();
  const [leaveDialogOpen, setLeaveDialogOpen] = useState(false);
  const [pendingHref, setPendingHref] = useState<string | null>(null);
  const [isSavingLeave, setIsSavingLeave] = useState(false);

  const needsLeavePrompt = useCallback(() => true, []);

  const persistTitle = useCallback(
    async (nextTitle: string) => {
      const trimmed = nextTitle.trim() || DEFAULT_NOTEBOOK_TITLE;
      const data = await updateNotebook.mutateAsync({
        notebookId: notebook.id,
        title: trimmed,
        touchLastStudied: true,
      });
      markTitleSaved(trimmed);
      return data;
    },
    [updateNotebook, notebook.id, markTitleSaved],
  );

  const completeNavigation = useCallback(
    (href: string) => {
      setLeaveDialogOpen(false);
      setPendingHref(null);
      router.push(href);
    },
    [router],
  );

  const tryNavigate = useCallback(
    (href: string) => {
      if (needsLeavePrompt()) {
        setPendingHref(href);
        setLeaveDialogOpen(true);
        return;
      }
      router.push(href);
    },
    [needsLeavePrompt, router],
  );

  useEffect(() => {
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!needsLeavePrompt()) return;
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', onBeforeUnload);
    return () => window.removeEventListener('beforeunload', onBeforeUnload);
  }, [needsLeavePrompt]);

  useEffect(() => {
    const onPopState = () => {
      if (!needsLeavePrompt()) return;
      window.history.pushState(null, '', window.location.href);
      setPendingHref('/library');
      setLeaveDialogOpen(true);
    };
    window.history.pushState(null, '', window.location.href);
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, [needsLeavePrompt]);

  const handleSaveAndLeave = async () => {
    const trimmed = title.trim();
    if (!trimmed || trimmed.toLowerCase() === DEFAULT_NOTEBOOK_TITLE.toLowerCase()) {
      return;
    }

    const destination = pendingHref || '/library';
    setIsSavingLeave(true);

    try {
      await persistTitle(trimmed);
      setLeaveDialogOpen(false);
      await showToast('Notebook saved', { minVisibleMs: TOAST_MIN_VISIBLE_MS });
      completeNavigation(destination);
    } catch {
      showToast('Could not save notebook');
    } finally {
      setIsSavingLeave(false);
    }
  };

  const value = useMemo(
    () => ({ tryNavigate, needsLeavePrompt }),
    [tryNavigate, needsLeavePrompt],
  );

  return (
    <NotebookLeaveGuardContext.Provider value={value}>
      {children}
      <NotebookSaveNameDialog
        open={leaveDialogOpen}
        title={title}
        isSaving={isSavingLeave || updateNotebook.isPending}
        onTitleChange={setTitle}
        onSave={handleSaveAndLeave}
        onLeaveAnyway={() => completeNavigation(pendingHref || '/library')}
        onCancel={() => {
          setLeaveDialogOpen(false);
          setPendingHref(null);
        }}
      />
    </NotebookLeaveGuardContext.Provider>
  );
}

export function useNotebookLeaveGuard() {
  const ctx = useContext(NotebookLeaveGuardContext);
  if (!ctx) {
    throw new Error('useNotebookLeaveGuard must be used within NotebookLeaveGuard');
  }
  return ctx;
}

export function useNotebookLeaveGuardOptional() {
  return useContext(NotebookLeaveGuardContext);
}
