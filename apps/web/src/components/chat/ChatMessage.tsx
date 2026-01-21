/**
 * Chat Message Component
 * 
 * Displays individual chat messages with citations.
 * Task B: Citation Display - Citations are clickable and open a modal.
 */

'use client';

import { useState } from 'react';
import { MessageCircle, User, Copy, Check, Bookmark, ThumbsUp, ThumbsDown } from 'lucide-react';
import { CitationModal } from './CitationModal';
import { apiClient } from '@/lib/api-client';
import { handleApiError, getUserFriendlyMessage } from '@/lib/error-handler';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

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
}

export function ChatMessage({ 
  role, 
  content, 
  citations = [], 
  timestamp,
  messageId,
  feedback: initialFeedback,
  onFeedbackUpdate,
  question
}: ChatMessageProps) {
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);
  const [isSavingNote, setIsSavingNote] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [feedback, setFeedback] = useState<'thumbs_up' | 'thumbs_down' | null>(initialFeedback || null);

  // Task B.e: Handle citation click
  const handleCitationClick = (citation: Citation) => {
    setSelectedCitation(citation);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setSelectedCitation(null);
  };

  // Copy button functionality
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
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
      await apiClient.createNote(content);
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

  // Render citation badge component
  const renderCitationBadge = (citationNum: number, numIndex: number, totalNumbers: number) => {
    const citation = citations[citationNum - 1];
    if (citation) {
      return (
        <span key={numIndex}>
          {numIndex > 0 && ', '}
          <button
            onClick={() => handleCitationClick(citation)}
            className="
              bg-citation-badge 
              text-[#E3E3E3] 
              px-1.5 
              rounded 
              text-xs 
              cursor-pointer
              hover:bg-surface-hover
              hover:text-text-primary
              transition-colors
              align-super
              font-medium
            "
            title={`Click to view citation: ${citation.sourceTitle || 'Source'}`}
            aria-label={`View citation ${citationNum} from ${citation.sourceTitle || 'source'}`}
          >
            {citationNum}
          </button>
        </span>
      );
    }
    // Fallback if citation not found
    return (
      <span key={numIndex}>
        {numIndex > 0 && ', '}
        <span
          className="
            bg-citation-badge 
            text-[#E3E3E3] 
            px-1.5 
            rounded 
            text-xs 
            align-super
          "
        >
          {citationNum}
        </span>
      </span>
    );
  };

  // Parse citations in content and render with markdown formatting
  const renderContentWithCitations = () => {
    // Helper to replace citation patterns in text
    const replaceCitationsInText = (text: string): React.ReactNode => {
      const citationPattern = /\[(\d+(?:\s*,\s*\d+)*)\]/g;
      const parts: React.ReactNode[] = [];
      let lastIndex = 0;
      let match;
      let keyCounter = 0;
      
      citationPattern.lastIndex = 0;
      
      while ((match = citationPattern.exec(text)) !== null) {
        // Add text before citation
        if (match.index > lastIndex) {
          parts.push(text.substring(lastIndex, match.index));
        }
        
        // Parse citation numbers
        const numbersStr = match[1];
        const numbers = numbersStr.split(',').map(num => parseInt(num.trim(), 10));
        
        // Render citation badge
        parts.push(
          <span key={`cite-${keyCounter++}`} className="inline-flex items-baseline">
            [
            {numbers.map((citationNum, numIndex) => 
              renderCitationBadge(citationNum, numIndex, numbers.length)
            )}
            ]
          </span>
        );
        
        lastIndex = match.index + match[0].length;
      }
      
      // Add remaining text
      if (lastIndex < text.length) {
        parts.push(text.substring(lastIndex));
      }
      
      return parts.length > 0 ? <>{parts}</> : text;
    };
    
    // Render markdown with custom text component that replaces citations
    return (
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children, ...props }) => <h1 className="text-2xl font-bold text-text-primary mt-6 mb-3" {...props}>{children}</h1>,
          h2: ({ children, ...props }) => <h2 className="text-xl font-semibold text-text-primary mt-5 mb-2" {...props}>{children}</h2>,
          h3: ({ children, ...props }) => <h3 className="text-lg font-semibold text-text-primary mt-4 mb-2" {...props}>{children}</h3>,
          ul: ({ children, ...props }) => <ul className="list-disc list-inside space-y-1 my-3 ml-4" {...props}>{children}</ul>,
          ol: ({ children, ...props }) => <ol className="list-decimal list-inside space-y-1 my-3 ml-4" {...props}>{children}</ol>,
          li: ({ children, ...props }) => <li className="text-text-primary" {...props}>{children}</li>,
          code: ({ children, className, ...props }: any) => {
            const isInline = !className;
            // Don't process citations in code blocks
            return isInline ? (
              <code className="bg-surface-subtle px-1.5 py-0.5 rounded text-sm font-mono text-text-primary" {...props}>{children}</code>
            ) : (
              <code className="block bg-surface-subtle p-3 rounded-lg text-sm font-mono text-text-primary overflow-x-auto my-3" {...props}>{children}</code>
            );
          },
          p: ({ children, ...props }) => <p className="mb-3 last:mb-0" {...props}>{children}</p>,
          br: () => <br />,
          strong: ({ children, ...props }) => <strong className="font-semibold text-text-primary" {...props}>{children}</strong>,
          em: ({ children, ...props }) => <em className="italic" {...props}>{children}</em>,
          // Replace citations in text nodes
          text: ({ children, ...props }: any) => {
            if (typeof children === 'string' && /\[\d+/.test(children)) {
              return <>{replaceCitationsInText(children)}</>;
            }
            return <>{children}</>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    );
  };

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
          {renderContentWithCitations()}
        </div>
        {/* Task B.e: Make citations clickable in the list as well */}
        {citations.length > 0 && (
          <div className="mt-3 space-y-1">
            {citations.map((citation, index) => {
              // Ensure unique key: combine available identifiers to prevent duplicate key warnings
              const uniqueKey = citation.id 
                ? `citation-${citation.id}` 
                : citation.chunk_id 
                ? `chunk-${citation.chunk_id}-${index}` 
                : `citation-${index}`;
              
              return (
              <button
                key={uniqueKey}
                onClick={() => handleCitationClick(citation)}
                className="
                  w-full text-left text-xs text-text-secondary 
                  border-l-2 border-border-default pl-2 py-1
                  hover:bg-surface-subtle hover:text-text-primary
                  rounded-r-lg transition-colors
                  cursor-pointer
                "
                title="Click to view full citation details"
              >
                <span className="text-accent-blue font-semibold">[{index + 1}]</span>{' '}
                <span className="font-medium">{citation.sourceTitle || 'Source'}</span>
                {': '}
                <span className="line-clamp-1">{citation.text}</span>
              </button>
              );
            })}
          </div>
        )}

        {/* Task B.b: Citation Modal */}
        <CitationModal
          citation={selectedCitation}
          isOpen={isModalOpen}
          onClose={handleCloseModal}
          question={question}
        />
        
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
