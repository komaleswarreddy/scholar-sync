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
}

export function ChatMessage({ 
  role, 
  content, 
  citations = [], 
  timestamp,
  messageId,
  feedback: initialFeedback,
  onFeedbackUpdate
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
    } catch (error) {
      console.error('Failed to save note:', error);
      alert('Failed to save message to notes. Please try again.');
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
    } catch (error) {
      console.error('Failed to update feedback:', error);
      // Revert on error
      setFeedback(feedback);
      alert('Failed to update feedback. Please try again.');
    }
  };

  // Parse citations in content (format: [1], [2], etc.)
  const renderContentWithCitations = () => {
    const parts = content.split(/(\[\d+\])/g);
    
    return parts.map((part, index) => {
      if (part.match(/\[\d+\]/)) {
        const citationNum = parseInt(part.replace(/[\[\]]/g, ''));
        const citation = citations[citationNum - 1];
        
        if (citation) {
          return (
            <span key={index}>
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
                {part}
              </button>
            </span>
          );
        }
        
        // Fallback if citation not found
        return (
          <span key={index}>
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
              {part}
            </span>
          </span>
        );
      }
      return <span key={index}>{part}</span>;
    });
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
        <p className="text-base text-text-primary leading-relaxed">
          {renderContentWithCitations()}
        </p>
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

