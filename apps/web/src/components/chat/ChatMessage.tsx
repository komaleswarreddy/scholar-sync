/**
 * Chat Message Component
 *
 * Assistant text is shown without inline [1] markers or source blocks; citations may still be stored for the backend.
 */

'use client';

import { useState, useEffect } from 'react';
import { MessageCircle, User, Copy, Check, Bookmark, ThumbsUp, ThumbsDown } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { handleApiError, getUserFriendlyMessage } from '@/lib/error-handler';
import { RichMarkdown } from '@/components/common/RichMarkdown';
import { NotebookDislikeReasonModal } from './NotebookDislikeReasonModal';

/** Remove citation UI noise and trailing suggested-question sections from model text. */
export function displayAssistantText(raw: string): string {
  let t = (raw || '').replace(/\[\d+(?:\s*,\s*\d+)*\]/g, '');
  const cut = t.search(/\[\d+\]\s*Source:/i);
  if (cut !== -1) {
    t = t.slice(0, cut);
  }
  t = t.replace(/\n---?\n+\s*##\s*Suggested questions\b.*/is, '');
  t = t.replace(/\n+\s*##\s*Suggested questions\b.*/is, '');
  t = t.replace(/\n+\s*Suggested follow-up questions\b.*/is, '');
  return t.replace(/\n{3,}/g, '\n\n').trim();
}

interface Citation {
  id?: string;
  sourceId?: string;
  sourceTitle?: string;
  text: string;
  source_id?: string;
  chunk_id?: string;
  page_number?: number;
  score?: number;
}

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  timestamp?: string;
  messageId?: string;
  feedback?: 'thumbs_up' | 'thumbs_down' | null;
  onFeedbackUpdate?: (
    messageId: string,
    feedback: 'thumbs_up' | 'thumbs_down' | null,
    feedbackReason?: string | null
  ) => void;
  question?: string;
  followUps?: string[];
  followUpsLoading?: boolean;
  onFollowUpClick?: (question: string) => void;
  appearance?: 'dashboard' | 'notebook';
  /** Hide notebook footer actions while the assistant message is still streaming */
  showActions?: boolean;
}

export function ChatMessage({ 
  role, 
  content, 
  citations: _citations = [],
  timestamp,
  messageId,
  feedback: initialFeedback,
  onFeedbackUpdate,
  question: _question,
  followUps = [],
  followUpsLoading = false,
  onFollowUpClick,
  appearance = 'dashboard',
  showActions = true,
}: ChatMessageProps) {
  const isNotebook = appearance === 'notebook';
  const [copySuccess, setCopySuccess] = useState(false);
  const [isSavingNote, setIsSavingNote] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [feedback, setFeedback] = useState<'thumbs_up' | 'thumbs_down' | null>(initialFeedback || null);
  const [dislikeModalOpen, setDislikeModalOpen] = useState(false);

  useEffect(() => {
    setFeedback(initialFeedback || null);
  }, [initialFeedback, messageId]);

  const textForUser = role === 'assistant' ? displayAssistantText(content) : content;

  // Copy button functionality
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(textForUser);
      setCopySuccess(true);
      setTimeout(() => {
        setCopySuccess(false);
      }, 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  // Save to Note functionality
  const handleSaveToNote = async () => {
    try {
      setIsSavingNote(true);
      await apiClient.createNote(textForUser);
      setSaveSuccess(true);
      
      // Dispatch custom event to notify NotesSection to refresh
      window.dispatchEvent(new CustomEvent('noteCreated'));
      
      setTimeout(() => {
        setSaveSuccess(false);
      }, 2000);
    } catch (error: any) {
      console.error('Failed to save note:', error);
      // Use standardized error handling
      const apiError = error.apiError || handleApiError(error);
      const errorMessage = getUserFriendlyMessage(apiError);
      // Show error in a user-friendly way (could be improved with toast notification)
      alert(errorMessage);
    } finally {
      setIsSavingNote(false);
    }
  };

  // Thumbs Up/Down feedback functionality
  const handleFeedback = async (newFeedback: 'thumbs_up' | 'thumbs_down') => {
    if (!messageId) {
      console.error('Cannot update feedback: messageId is required');
      return;
    }

    // Toggle feedback: if clicking the same button, remove feedback
    const updatedFeedback = feedback === newFeedback ? null : newFeedback;
    
    try {
      setFeedback(updatedFeedback);
      
      // Call backend to update feedback
      await apiClient.updateMessageFeedback(messageId, updatedFeedback);
      
      // Notify parent component if callback provided
      if (onFeedbackUpdate) {
        onFeedbackUpdate(messageId, updatedFeedback, null);
      }
    } catch (error: any) {
      console.error('Failed to update feedback:', error);
      // Revert on error
      setFeedback(feedback);
      // Use standardized error handling
      const apiError = error.apiError || handleApiError(error);
      const errorMessage = getUserFriendlyMessage(apiError);
      // Show error in a user-friendly way (could be improved with toast notification)
      alert(errorMessage);
    }
  };

  const handleNotebookThumbsUp = async () => {
    if (!messageId) return;
    const updatedFeedback = feedback === 'thumbs_up' ? null : 'thumbs_up';
    const previous = feedback;
    try {
      setFeedback(updatedFeedback);
      await apiClient.updateMessageFeedback(messageId, updatedFeedback);
      onFeedbackUpdate?.(messageId, updatedFeedback, null);
    } catch (error: unknown) {
      setFeedback(previous);
      const apiError = (error as { apiError?: ReturnType<typeof handleApiError> }).apiError || handleApiError(error);
      alert(getUserFriendlyMessage(apiError));
    }
  };

  const handleNotebookThumbsDownClick = () => {
    if (!messageId) return;
    if (feedback === 'thumbs_down') {
      void handleNotebookDislikeSubmit(null);
      return;
    }
    setDislikeModalOpen(true);
  };

  const handleNotebookDislikeSubmit = async (reason: string | null) => {
    if (!messageId) return;
    const updatedFeedback = reason ? 'thumbs_down' : null;
    const previous = feedback;
    try {
      setFeedback(updatedFeedback);
      await apiClient.updateMessageFeedback(messageId, updatedFeedback, reason ?? undefined);
      onFeedbackUpdate?.(messageId, updatedFeedback, reason);
    } catch (error: unknown) {
      setFeedback(previous);
      const apiError = (error as { apiError?: ReturnType<typeof handleApiError> }).apiError || handleApiError(error);
      throw new Error(getUserFriendlyMessage(apiError));
    }
  };

  const renderAssistantMarkdown = () => (
    <RichMarkdown content={textForUser} variant="chat" />
  );

  if (role === 'user') {
    if (isNotebook) {
      return (
        <div className="flex justify-end">
          <div className="notebook-user-bubble">
            <p className="text-[14px] leading-relaxed">{content}</p>
            {timestamp && (
              <p className="text-[10px] opacity-80 mt-1.5 text-right">{timestamp}</p>
            )}
          </div>
        </div>
      );
    }

    return (
      <div className="flex items-start gap-3 p-4">
        <div className="w-8 h-8 rounded-full bg-surface flex items-center justify-center flex-shrink-0">
          <User className="w-4 h-4 text-text-secondary" />
        </div>
        <div className="flex-1">
          <p className="text-base text-text-primary leading-relaxed">{content}</p>
          <div className="flex items-center gap-3 mt-2">
            <button
              onClick={handleCopy}
              className="flex items-center gap-2 px-3 py-1.5 text-xs bg-surface border border-border-default rounded-full text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors"
              title="Copy message to clipboard"
              aria-label="Copy message"
            >
              {copySuccess ? (
                <>
                  <Check className="w-3 h-3" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  Copy
                </>
              )}
            </button>
            <button
              onClick={handleSaveToNote}
              disabled={isSavingNote}
              className="flex items-center gap-2 px-3 py-1.5 text-xs bg-surface border border-border-default rounded-full text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title="Save message to notes"
              aria-label="Save message to notes"
            >
              {saveSuccess ? (
                <>
                  <Check className="w-3 h-3" />
                  Saved!
                </>
              ) : (
                <>
                  <Bookmark className={`w-3 h-3 ${isSavingNote ? 'animate-pulse' : ''}`} />
                  {isSavingNote ? 'Saving...' : 'Save to note'}
                </>
              )}
            </button>
            {timestamp && (
              <p className="text-xs text-text-tertiary">{timestamp}</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (isNotebook) {
    return (
      <>
        <div className="flex items-start gap-2.5">
          <div className="notebook-ai-avatar" aria-hidden>
            AI
          </div>
          <div className="flex-1 min-w-0 pt-0.5">
            <div
              className="text-[14px] text-[var(--color-home-text)] leading-relaxed prose prose-sm max-w-none"
              data-assistant-content="true"
            >
              {renderAssistantMarkdown()}
            </div>
            {showActions && (
              <div className="notebook-message-actions">
                <button
                  type="button"
                  onClick={() => void handleCopy()}
                  className="notebook-message-action-btn"
                  title="Copy response"
                  aria-label="Copy response"
                >
                  {copySuccess ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                </button>
                <button
                  type="button"
                  onClick={() => void handleNotebookThumbsUp()}
                  disabled={!messageId}
                  className={`notebook-message-action-btn ${
                    feedback === 'thumbs_up' ? 'notebook-message-action-btn--active' : ''
                  }`}
                  title={feedback === 'thumbs_up' ? 'Remove like' : 'Like'}
                  aria-label={feedback === 'thumbs_up' ? 'Remove like' : 'Like response'}
                  aria-pressed={feedback === 'thumbs_up'}
                >
                  <ThumbsUp
                    className="w-4 h-4 notebook-feedback-icon"
                    fill={feedback === 'thumbs_up' ? 'currentColor' : 'none'}
                    strokeWidth={feedback === 'thumbs_up' ? 0 : 2}
                  />
                </button>
                <button
                  type="button"
                  onClick={handleNotebookThumbsDownClick}
                  disabled={!messageId}
                  className={`notebook-message-action-btn ${
                    feedback === 'thumbs_down' ? 'notebook-message-action-btn--active' : ''
                  }`}
                  title={feedback === 'thumbs_down' ? 'Remove dislike' : 'Dislike'}
                  aria-label={feedback === 'thumbs_down' ? 'Remove dislike' : 'Dislike response'}
                  aria-pressed={feedback === 'thumbs_down'}
                >
                  <ThumbsDown
                    className="w-4 h-4 notebook-feedback-icon"
                    fill={feedback === 'thumbs_down' ? 'currentColor' : 'none'}
                    strokeWidth={feedback === 'thumbs_down' ? 0 : 2}
                  />
                </button>
              </div>
            )}
            {showActions && followUpsLoading && onFollowUpClick && (
              <div className="notebook-follow-up-chips" aria-busy="true" aria-label="Loading follow-up suggestions">
                <span className="notebook-follow-up-chip notebook-follow-up-chip--loading">
                  Suggesting questions…
                </span>
              </div>
            )}
            {showActions && !followUpsLoading && followUps.length > 0 && onFollowUpClick && (
              <div className="notebook-follow-up-chips">
                {followUps.map((item) => (
                  <button
                    key={item}
                    type="button"
                    className="notebook-follow-up-chip"
                    onClick={() => onFollowUpClick(item)}
                  >
                    {item}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
        <NotebookDislikeReasonModal
          open={dislikeModalOpen}
          onClose={() => setDislikeModalOpen(false)}
          onSubmit={async (reason) => {
            await handleNotebookDislikeSubmit(reason);
          }}
        />
      </>
    );
  }

  return (
    <div className="flex items-start gap-3 p-4">
      <div className="w-8 h-8 rounded-full bg-surface flex items-center justify-center flex-shrink-0">
        <MessageCircle className="w-4 h-4 text-accent-blue" />
      </div>
        <div className="flex-1">
          <div className="text-base text-text-primary leading-relaxed prose prose-invert max-w-none">
          {renderAssistantMarkdown()}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3 mt-3">
          <button
            onClick={handleCopy}
            className="flex items-center gap-2 px-3 py-1.5 text-xs bg-surface border border-border-default rounded-full text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors"
            title="Copy message to clipboard"
            aria-label="Copy message"
          >
            {copySuccess ? (
              <>
                <Check className="w-3 h-3" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                Copy
              </>
            )}
          </button>
          <button
            onClick={handleSaveToNote}
            disabled={isSavingNote}
            className="flex items-center gap-2 px-3 py-1.5 text-xs bg-surface border border-border-default rounded-full text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Save message to notes"
            aria-label="Save message to notes"
          >
            {saveSuccess ? (
              <>
                <Check className="w-3 h-3" />
                Saved!
              </>
            ) : (
              <>
                <Bookmark className={`w-3 h-3 ${isSavingNote ? 'animate-pulse' : ''}`} />
                {isSavingNote ? 'Saving...' : 'Save to note'}
              </>
            )}
          </button>
          {/* Thumbs Up/Down Feedback - Show for all assistant messages */}
          {role === 'assistant' && (
            <>
              <button
                onClick={() => handleFeedback('thumbs_up')}
                className={`p-1.5 rounded-full transition-colors ${
                  feedback === 'thumbs_up'
                    ? 'bg-accent-blue/20 text-accent-blue'
                    : 'hover:bg-surface-hover text-text-secondary'
                }`}
                title={feedback === 'thumbs_up' ? 'Remove thumbs up' : 'Thumbs up'}
                aria-label={feedback === 'thumbs_up' ? 'Remove thumbs up feedback' : 'Give thumbs up feedback'}
                disabled={!messageId}
              >
                <ThumbsUp className="w-4 h-4" />
              </button>
              <button
                onClick={() => handleFeedback('thumbs_down')}
                className={`p-1.5 rounded-full transition-colors ${
                  feedback === 'thumbs_down'
                    ? 'bg-red-500/20 text-red-500'
                    : 'hover:bg-surface-hover text-text-secondary'
                }`}
                title={feedback === 'thumbs_down' ? 'Remove thumbs down' : 'Thumbs down'}
                aria-label={feedback === 'thumbs_down' ? 'Remove thumbs down feedback' : 'Give thumbs down feedback'}
                disabled={!messageId}
              >
                <ThumbsDown className="w-4 h-4" />
              </button>
            </>
          )}
          {timestamp && (
            <p className="text-xs text-text-tertiary">{timestamp}</p>
          )}
        </div>
      </div>
    </div>
  );
}
