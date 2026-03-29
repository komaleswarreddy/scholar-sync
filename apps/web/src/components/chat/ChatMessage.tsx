/**
 * Chat Message Component
 *
 * Assistant text is shown without inline [1] markers or source blocks; citations may still be stored for the backend.
 */

'use client';

import { useState } from 'react';
import { MessageCircle, User, Copy, Check, Bookmark, ThumbsUp, ThumbsDown } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { handleApiError, getUserFriendlyMessage } from '@/lib/error-handler';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/** Remove citation UI noise from model text (inline [1] and trailing [n] Source: blocks). */
export function displayAssistantText(raw: string): string {
  let t = (raw || '').replace(/\[\d+(?:\s*,\s*\d+)*\]/g, '');
  const cut = t.search(/\[\d+\]\s*Source:/i);
  if (cut !== -1) {
    t = t.slice(0, cut);
  }
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
  onFeedbackUpdate?: (messageId: string, feedback: 'thumbs_up' | 'thumbs_down' | null) => void;
  question?: string;
  followUps?: string[];
  onFollowUpClick?: (question: string) => void;
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
  onFollowUpClick,
}: ChatMessageProps) {
  const [copySuccess, setCopySuccess] = useState(false);
  const [isSavingNote, setIsSavingNote] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [feedback, setFeedback] = useState<'thumbs_up' | 'thumbs_down' | null>(initialFeedback || null);

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
        onFeedbackUpdate(messageId, updatedFeedback);
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

  const renderAssistantMarkdown = () => (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children, ...props }) => <h1 className="text-2xl font-bold text-text-primary mt-6 mb-3 first:mt-0" {...props}>{children}</h1>,
        h2: ({ children, ...props }) => <h2 className="text-xl font-semibold text-text-primary mt-6 mb-2 first:mt-0" {...props}>{children}</h2>,
        h3: ({ children, ...props }) => <h3 className="text-lg font-semibold text-text-primary mt-5 mb-2 first:mt-0" {...props}>{children}</h3>,
        ul: ({ children, ...props }) => <ul className="list-disc list-outside space-y-2 my-4 ml-5 pl-1" {...props}>{children}</ul>,
        ol: ({ children, ...props }) => <ol className="list-decimal list-outside space-y-2 my-4 ml-5 pl-1" {...props}>{children}</ol>,
        li: ({ children, ...props }) => <li className="text-text-primary" {...props}>{children}</li>,
        code: ({ children, className, ...props }: any) => {
          const isInline = !className;
          return isInline ? (
            <code className="bg-surface-subtle px-1.5 py-0.5 rounded text-sm font-mono text-text-primary" {...props}>{children}</code>
          ) : (
            <code className="block bg-surface-subtle p-3 rounded-lg text-sm font-mono text-text-primary overflow-x-auto my-3" {...props}>{children}</code>
          );
        },
        p: ({ children, ...props }) => <p className="mb-3 last:mb-0 leading-relaxed" {...props}>{children}</p>,
        br: () => <br />,
        hr: () => <hr className="my-5 border-0 border-t border-border-default" />,
        strong: ({ children, ...props }) => <strong className="font-semibold text-text-primary" {...props}>{children}</strong>,
        em: ({ children, ...props }) => <em className="italic" {...props}>{children}</em>,
      }}
    >
      {textForUser}
    </ReactMarkdown>
  );

  if (role === 'user') {
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

  return (
    <div className="flex items-start gap-3 p-4">
      <div className="w-8 h-8 rounded-full bg-surface flex items-center justify-center flex-shrink-0">
        <MessageCircle className="w-4 h-4 text-accent-blue" />
      </div>
        <div className="flex-1">
          <div className="text-base text-text-primary leading-relaxed prose prose-invert max-w-none">
          {renderAssistantMarkdown()}
        </div>

        {followUps.length > 0 && (
          <div className="mt-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-text-tertiary mb-2">
              Suggested follow-up questions
            </p>
            <div className="flex flex-wrap gap-2">
              {followUps.map((q, idx) => (
                <button
                  key={`${idx}-${q}`}
                  onClick={() => onFollowUpClick?.(q)}
                  className="px-3 py-1.5 text-xs bg-surface border border-border-default rounded-full text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors"
                  title="Ask this follow-up question"
                  aria-label={`Ask follow-up question: ${q}`}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

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
