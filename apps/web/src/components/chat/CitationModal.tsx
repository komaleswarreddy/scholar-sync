/**
 * Citation Modal Component
 * 
 * Displays citation details when a citation is clicked.
 * Shows source text, metadata (title, page, score), and source information.
 */

'use client';

import { X, FileText, BookOpen, TrendingUp } from 'lucide-react';
import { useEffect } from 'react';

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

interface CitationModalProps {
  citation: Citation | null;
  isOpen: boolean;
  onClose: () => void;
}

export function CitationModal({ citation, isOpen, onClose }: CitationModalProps) {
  // Close modal on Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      // Prevent body scroll when modal is open
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen || !citation) return null;

  // Get source title - prefer sourceTitle, fallback to source_id
  const sourceTitle = citation.sourceTitle || citation.sourceId || citation.source_id || 'Unknown Source';
  const pageNumber = citation.page_number;
  const score = citation.score;
  
  // Handle score: Pinecone returns 0.0-1.0, but check if it's already a percentage (0-100)
  // If score > 1, assume it's already a percentage; otherwise multiply by 100
  const formatScore = (scoreValue: number | undefined): string => {
    if (scoreValue === undefined || scoreValue === null) return 'N/A';
    // If score is > 1, assume it's already a percentage (0-100)
    // Otherwise, assume it's a decimal (0.0-1.0) and convert to percentage
    const percentage = scoreValue > 1 ? scoreValue : scoreValue * 100;
    return `${percentage.toFixed(1)}%`;
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="citation-modal-title"
          aria-describedby="citation-modal-description"
          className="bg-surface border border-border-default rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-border-default">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-accent-blue/10 flex items-center justify-center">
                <FileText className="w-5 h-5 text-accent-blue" />
              </div>
              <div>
                <h2 id="citation-modal-title" className="text-lg font-bold text-text-primary">Citation Details</h2>
                <p id="citation-modal-description" className="text-xs text-text-tertiary mt-0.5">Source reference information</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-surface-hover transition-colors text-text-secondary hover:text-text-primary"
              aria-label="Close modal"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Source Metadata */}
            <div className="space-y-4">
              <div className="flex items-start gap-3 p-4 bg-surface-subtle rounded-xl border border-border-default">
                <BookOpen className="w-4 h-4 text-text-secondary mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-bold text-text-tertiary uppercase tracking-wider mb-1">
                    Source
                  </p>
                  <p className="text-sm font-semibold text-text-primary break-words">
                    {sourceTitle}
                  </p>
                </div>
              </div>

              {/* Metadata Row */}
              <div className="grid grid-cols-2 gap-3">
                {/* Page Number */}
                {pageNumber !== undefined && pageNumber !== null && (
                  <div className="p-4 bg-surface-subtle rounded-xl border border-border-default">
                    <p className="text-xs font-bold text-text-tertiary uppercase tracking-wider mb-1">
                      Page
                    </p>
                    <p className="text-base font-semibold text-text-primary">
                      {pageNumber}
                    </p>
                  </div>
                )}

                {/* Relevance Score */}
                {score !== undefined && score !== null && (
                  <div className="p-4 bg-surface-subtle rounded-xl border border-border-default">
                    <div className="flex items-center gap-2 mb-1">
                      <TrendingUp className="w-3.5 h-3.5 text-text-tertiary" />
                      <p className="text-xs font-bold text-text-tertiary uppercase tracking-wider">
                        Relevance Score
                      </p>
                    </div>
                    <p className="text-base font-semibold text-text-primary">
                      {formatScore(score)}
                    </p>
                  </div>
                )}
              </div>

              {/* Chunk ID (if available) */}
              {citation.chunk_id && (
                <div className="p-3 bg-surface-subtle rounded-lg border border-border-default">
                  <p className="text-xs font-medium text-text-tertiary">
                    Chunk ID: <span className="font-mono text-text-secondary">{citation.chunk_id}</span>
                  </p>
                </div>
              )}
            </div>

            {/* Source Text */}
            <div className="space-y-2">
              <p className="text-xs font-bold text-text-tertiary uppercase tracking-wider">
                Source Text
              </p>
              <div className="p-4 bg-surface-subtle rounded-xl border border-border-default">
                <p className="text-sm text-text-primary leading-relaxed whitespace-pre-wrap">
                  {citation.text || 'No text available'}
                </p>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="p-6 border-t border-border-default flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-accent-blue text-background rounded-lg font-semibold text-sm hover:opacity-90 transition-opacity"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
