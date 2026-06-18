'use client';

import { useRef, useState, KeyboardEvent, useEffect } from 'react';
import { ArrowUp, Loader2, Paperclip } from 'lucide-react';
import { useNotebookContext } from '@/contexts/NotebookContext';
import { useProblemSolverContext } from '@/contexts/ProblemSolverContext';
import { useUploadSource } from '@/hooks/useSources';
import { useExtractProblemSolverFromSource } from '@/hooks/useProblemSolver';
import { apiClient } from '@/lib/api-client';
import { getUserFriendlyMessage, handleApiError } from '@/lib/error-handler';

const ACCEPTED_TYPES = 'image/*,.pdf,application/pdf';

export function ProblemSolverComposer() {
  const { notebook } = useNotebookContext();
  const {
    session,
    submitProblem,
    triggerFollowUp,
    setExtracting,
    isStreaming,
    isFollowUpLoading,
  } = useProblemSolverContext();
  const uploadSource = useUploadSource(notebook.id);
  const extractFromSource = useExtractProblemSolverFromSource();

  const [message, setMessage] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const busy = isSubmitting || isStreaming || isFollowUpLoading;
  const hasActiveSession = Boolean(session?.session_id);
  const canFollowUp = hasActiveSession && Boolean(session?.solving_mode);

  useEffect(() => {
    if (!textareaRef.current) return;
    const el = textareaRef.current;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 72)}px`;
  }, [message]);

  const handleFile = async (file: File) => {
    setError(null);
    setIsSubmitting(true);
    setExtracting(true);
    try {
      const uploaded = await uploadSource.mutateAsync({ file, title: file.name });
      const sourceId = uploaded?.id as string | undefined;
      if (!sourceId) throw new Error('Upload did not return a source id');

      let indexed = false;
      for (let attempt = 0; attempt < 30; attempt++) {
        await new Promise((r) => setTimeout(r, 2000));
        const list = (await apiClient.listSources(notebook.id)) as Array<{
          id: string;
          status: string;
          error_message?: string | null;
        }>;
        const source = list.find((s) => s.id === sourceId);
        if (source?.status === 'indexed' || source?.status === 'completed') {
          indexed = true;
          break;
        }
        if (source?.status === 'error' || source?.status === 'failed') {
          throw new Error(source.error_message || 'File processing failed');
        }
      }
      if (!indexed) throw new Error('File is still processing. Try again in a moment.');

      const { normalized_text } = await extractFromSource.mutateAsync(sourceId);
      await submitProblem(normalized_text, 'file', [{ source_id: sourceId, file_name: file.name }]);
      setMessage('');
    } catch (e: unknown) {
      const apiError = handleApiError(e);
      setError(getUserFriendlyMessage(apiError));
    } finally {
      setExtracting(false);
      setIsSubmitting(false);
    }
  };

  const handleSend = async () => {
    const trimmed = message.trim();
    if (!trimmed || busy) return;
    setError(null);
    setIsSubmitting(true);
    try {
      if (!hasActiveSession) {
        if (trimmed.length < 10) {
          setError('Please enter at least 10 characters describing your problem.');
          return;
        }
        await submitProblem(trimmed, 'text');
      } else if (canFollowUp) {
        await triggerFollowUp('CUSTOM_FOLLOW_UP', trimmed);
      }
      setMessage('');
    } catch (e: unknown) {
      const apiError = handleApiError(e);
      setError(getUserFriendlyMessage(apiError));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  const placeholder = !hasActiveSession
    ? 'Paste or type your problem…'
    : canFollowUp
      ? 'Ask a follow-up or pick an action above…'
      : 'Select a solving mode above to continue…';

  return (
    <div className="px-4 pb-3 pt-2 border-t border-border-default bg-surface flex-shrink-0">
      <div className="notebook-chat-composer notebook-chat-composer--minimal">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={busy}
          placeholder={placeholder}
          rows={1}
          className="notebook-chat-composer-input notebook-chat-composer-input--minimal"
          aria-label="Problem input"
        />
        <div className="notebook-chat-composer-toolbar">
          <div className="notebook-chat-composer-actions">
            <button
              type="button"
              className="notebook-chat-composer-icon-btn"
              title="Attach file"
              aria-label="Attach file"
              disabled={busy}
              onClick={() => fileInputRef.current?.click()}
            >
              <Paperclip className="w-[18px] h-[18px]" strokeWidth={1.75} />
            </button>
          </div>
          <button
            type="button"
            onClick={() => void handleSend()}
            disabled={busy || !message.trim()}
            className="notebook-send-btn notebook-send-btn--square disabled:cursor-not-allowed"
            title="Send"
            aria-label="Send"
          >
            {busy ? (
              <Loader2 className="w-[18px] h-[18px] animate-spin" strokeWidth={2} />
            ) : (
              <ArrowUp className="w-[18px] h-[18px]" strokeWidth={2.25} />
            )}
          </button>
        </div>
      </div>
      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED_TYPES}
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void handleFile(file);
          e.target.value = '';
        }}
      />
      {error ? <p className="text-xs text-red-600 mt-2">{error}</p> : null}
    </div>
  );
}
