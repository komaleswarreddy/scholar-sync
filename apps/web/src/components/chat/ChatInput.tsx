/**
 * Chat Input Component
 *
 * Input field for sending messages.
 */

'use client';

import { useState, KeyboardEvent, useMemo, useRef, useEffect } from 'react';
import { ArrowUp, ChevronDown, ImageIcon, Lightbulb, Paperclip, Send, Sigma } from 'lucide-react';
import { Input } from '../ui/Input';
import { useSources } from '@/hooks/useSources';
import { useNotebookScopeId } from '@/contexts/NotebookContext';
import { normalizeSourceId } from '@/hooks/useValidSelectedSourceIds';

interface ChatInputProps {
  onSend?: (message: string, activeSourceIds?: string[]) => void;
  disabled?: boolean;
  /** When set, only blocks send — input stays editable (notebook composer). */
  sendDisabled?: boolean;
  activeSourceIds?: string[];
  showSuggestedPrompts?: boolean;
  tutorSuggestions?: { label: string; prompt: string }[];
  helperText?: string;
  disabledReason?: string | null;
  appearance?: 'dashboard' | 'notebook';
}

const SUGGESTIONS_PREF_KEY = 'notebookChatSuggestionsExpanded';
const NOTEBOOK_SUGGESTION_LIMIT = 2;
const TUTOR_SUGGESTION_LIMIT = 4;

export function ChatInput({
  onSend,
  disabled = false,
  sendDisabled,
  activeSourceIds = [],
  showSuggestedPrompts = true,
  tutorSuggestions,
  helperText,
  disabledReason,
  appearance = 'dashboard',
}: ChatInputProps) {
  const isNotebook = appearance === 'notebook';
  const cannotSend = sendDisabled ?? disabled;
  const [message, setMessage] = useState('');
  const [suggestionsExpanded, setSuggestionsExpanded] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const notebookId = useNotebookScopeId();
  const { data: sources = [] } = useSources(notebookId);

  const selectedSources = useMemo(() => {
    if (activeSourceIds.length === 0) return [];
    return sources.filter((source) =>
      activeSourceIds.some((aid) => normalizeSourceId(aid) === normalizeSourceId(source.id))
    );
  }, [sources, activeSourceIds]);

  const suggestedPrompts = useMemo(() => {
    if (tutorSuggestions?.length) {
      return tutorSuggestions.slice(0, TUTOR_SUGGESTION_LIMIT);
    }

    const sourceContext =
      selectedSources.length === 0
        ? 'my selected sources'
        : selectedSources.length === 1
          ? `this document${selectedSources[0].title ? ` (${selectedSources[0].title})` : ''}`
          : 'these documents';

    return [
      {
        label: 'Main topics',
        prompt: `What are the main topics covered in ${sourceContext}?`,
      },
      {
        label: 'Summarize key points',
        prompt: `Summarize the key points from ${sourceContext}.`,
      },
    ];
  }, [selectedSources, tutorSuggestions]);

  const notebookSuggestionLimit = tutorSuggestions?.length ? TUTOR_SUGGESTION_LIMIT : NOTEBOOK_SUGGESTION_LIMIT;
  const visibleNotebookPrompts = suggestedPrompts.slice(0, notebookSuggestionLimit);

  useEffect(() => {
    if (!isNotebook) return;
    const stored = localStorage.getItem(SUGGESTIONS_PREF_KEY);
    if (stored === '1') setSuggestionsExpanded(true);
  }, [isNotebook]);

  const toggleSuggestions = () => {
    setSuggestionsExpanded((prev) => {
      const next = !prev;
      localStorage.setItem(SUGGESTIONS_PREF_KEY, next ? '1' : '0');
      return next;
    });
  };

  useEffect(() => {
    if (!isNotebook || !textareaRef.current) return;
    const el = textareaRef.current;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [message, isNotebook]);

  const handleSend = () => {
    if (message.trim() && !cannotSend) {
      onSend?.(message, activeSourceIds);
      setMessage('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement | HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (isNotebook) {
    return (
      <div className="px-0">
        {showSuggestedPrompts && visibleNotebookPrompts.length > 0 && (
          <div className="notebook-suggest-block mb-2">
            <button
              type="button"
              className="notebook-suggest-toggle"
              onClick={toggleSuggestions}
              aria-expanded={suggestionsExpanded}
              aria-controls="notebook-suggest-chips"
            >
              <Lightbulb className="w-3.5 h-3.5" strokeWidth={2} aria-hidden />
              <span>Suggestions</span>
              <ChevronDown
                className={`w-3.5 h-3.5 transition-transform ${suggestionsExpanded ? 'rotate-180' : ''}`}
                aria-hidden
              />
            </button>
            {suggestionsExpanded && (
              <div id="notebook-suggest-chips" className="flex flex-wrap gap-2 mt-2">
                {visibleNotebookPrompts.map((item, index) => (
                  <button
                    key={index}
                    type="button"
                    className="notebook-suggest-chip disabled:opacity-50 disabled:cursor-not-allowed"
                    onClick={() => setMessage(item.prompt)}
                    disabled={disabled}
                    title={item.prompt}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="notebook-chat-composer">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="Ask your tutor anything..."
            rows={1}
            className="notebook-chat-composer-input"
            aria-label="Message input"
          />
          <div className="notebook-chat-composer-toolbar">
            <div className="notebook-chat-composer-actions">
              <button
                type="button"
                className="notebook-chat-composer-icon-btn"
                title="Attach file"
                aria-label="Attach file"
                disabled={disabled}
              >
                <Paperclip className="w-[18px] h-[18px]" strokeWidth={1.75} />
              </button>
              <button
                type="button"
                className="notebook-chat-composer-icon-btn"
                title="Add image"
                aria-label="Add image"
                disabled={disabled}
              >
                <ImageIcon className="w-[18px] h-[18px]" strokeWidth={1.75} />
              </button>
              <button
                type="button"
                className="notebook-chat-composer-icon-btn"
                title="Insert math"
                aria-label="Insert math"
                disabled={disabled}
              >
                <Sigma className="w-[18px] h-[18px]" strokeWidth={1.75} />
              </button>
            </div>
            <button
              type="button"
              onClick={handleSend}
              disabled={cannotSend || !message.trim()}
              className="notebook-send-btn notebook-send-btn--square disabled:cursor-not-allowed"
              title="Send message"
              aria-label="Send message"
            >
              <ArrowUp className="w-[18px] h-[18px]" strokeWidth={2.25} />
            </button>
          </div>
        </div>

        <p className="notebook-chat-composer-disclaimer">
          {disabled
            ? disabledReason || 'Chat unavailable'
            : cannotSend && disabledReason
              ? disabledReason
              : 'AI can make mistakes. Please verify important information.'}
        </p>
      </div>
    );
  }

  return (
    <div className="p-4">
      {showSuggestedPrompts && suggestedPrompts.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {suggestedPrompts.slice(0, 2).map((item, index) => (
            <button
              key={index}
              type="button"
              className="px-4 py-2 text-xs bg-surface border border-border-default rounded-full text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={() => setMessage(item.prompt)}
              disabled={disabled}
              title={item.prompt}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}

      <div className="flex items-center gap-2 bg-surface border border-border-default rounded-full px-4 py-2">
        <Input
          type="text"
          placeholder="Start typing..."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          className="border-0 bg-transparent focus:ring-0 flex-1"
        />
        <button
          type="button"
          onClick={handleSend}
          disabled={cannotSend || !message.trim()}
          className="p-2 rounded-full bg-accent-blue text-background hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
          title="Send message"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>

      <div className="flex items-center justify-between mt-3 px-2">
        <p className="text-xs text-text-tertiary">
          {disabled ? disabledReason || 'Chat unavailable right now' : helperText || 'Chat ready'}
        </p>
        <p className="text-xs text-text-tertiary italic">
          NotebookLM can be inaccurate; please double check its responses.
        </p>
      </div>
    </div>
  );
}
