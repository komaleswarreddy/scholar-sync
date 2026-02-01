/**
 * Generation Modal Component
 * 
 * Reusable modal for displaying generated content from Studio tools.
 * Supports JSON, Markdown, and plain text content types.
 * Includes loading and error states.
 */

'use client';

import { useEffect, useState } from 'react';
import { X, Loader2, AlertCircle, Download, Copy, Check, RotateCcw } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from '../ui/Button';
import { LoadingShimmer } from '../ui/LoadingShimmer';
import { QuizDisplay } from './QuizDisplay';
import { FlashcardsDisplay } from './FlashcardsDisplay';
import { MindMapDisplay } from './MindMapDisplay';
import { ReportDisplay } from './ReportDisplay';
import { InfographicBriefDisplay } from './InfographicBriefDisplay';
import { SlideDeckDisplay } from './SlideDeckDisplay';

export type ContentType = 'json' | 'markdown' | 'text';

interface GenerationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave?: (content: string) => void | Promise<void>;
  onRetry?: () => void | Promise<void>;
  title?: string;
  contentType?: ContentType;
  content?: string | object | null;
  loading?: boolean;
  loadingType?: string;
  sourceCount?: number;
  customInstructions?: string;
  error?: string | null;
}

export function GenerationModal({
  isOpen,
  onClose,
  onSave,
  onRetry,
  title = 'Generated Content',
  contentType = 'text',
  content = null,
  loading = false,
  loadingType,
  sourceCount,
  customInstructions,
  error = null,
}: GenerationModalProps) {
  const [copied, setCopied] = useState(false);

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

  // Reset copied state when content changes
  useEffect(() => {
    setCopied(false);
  }, [content]);

  if (!isOpen) return null;

  // Check if content is a quiz
  const isQuizContent = (): boolean => {
    try {
      let parsed: any;
      
      if (typeof content === 'string') {
        parsed = JSON.parse(content);
      } else if (typeof content === 'object' && content !== null) {
        parsed = content;
      } else {
        return false;
      }

      // Check if it's a quiz response structure
      if (parsed.task_type === 'quiz' || (parsed.data && parsed.data.questions)) {
        return true;
      }
      
      // Check if it has quiz structure directly
      if (parsed.questions && Array.isArray(parsed.questions)) {
        return true;
      }

      return false;
    } catch {
      return false;
    }
  };

  // Check if content is flashcards
  const isFlashcardsContent = (): boolean => {
    try {
      let parsed: any;
      
      if (typeof content === 'string') {
        parsed = JSON.parse(content);
      } else if (typeof content === 'object' && content !== null) {
        parsed = content;
      } else {
        return false;
      }

      // Check if it's a flashcards response structure
      if (parsed.task_type === 'flashcards' || (parsed.data && Array.isArray(parsed.data) && parsed.data.length > 0 && parsed.data[0].front && parsed.data[0].back)) {
        return true;
      }
      
      // Check if it's a direct array of flashcards
      if (Array.isArray(parsed) && parsed.length > 0 && parsed[0].front && parsed[0].back) {
        return true;
      }

      return false;
    } catch {
      return false;
    }
  };

  // Check if content is a mind map
  const isMindMapContent = (): boolean => {
    try {
      let parsed: any;
      let contentString = '';
      
      if (typeof content === 'string') {
        contentString = content;
        try {
          parsed = JSON.parse(content);
          // If it's JSON, check for mind_map task_type
          if (parsed.task_type === 'mind_map') {
            return true;
          }
        } catch {
          // Not JSON, check if it looks like a mind map markdown
          // But first exclude slide deck and infographic patterns
          const slidePattern = /(?:^#+\s+.*[Ss]lide\s+\d+|^#+\s+Slide\s+\d+)/m;
          if (slidePattern.test(contentString)) {
            return false; // This is likely a slide deck, not a mind map
          }
          
          // Exclude infographic patterns
          const infographicKeywords = [
            /infographic/i,
            /visual\s+(?:elements?|brief|design)/i,
            /data\s+points?/i,
            /layout\s+(?:suggestions?|design)/i,
            /color\s+scheme/i,
          ];
          if (infographicKeywords.some(pattern => pattern.test(contentString))) {
            return false; // This is likely an infographic, not a mind map
          }
          
          // Mind maps typically have hierarchical headers (#, ##, ###) or structured lists
          // But should NOT have many top-level headers (that's a slide deck)
          const lines = contentString.split('\n');
          const topLevelHeaders = lines.filter(line => {
            const trimmed = line.trim();
            return trimmed.match(/^#{1,2}\s+/) && !trimmed.match(/^#{3,}/);
          });
          
          // If there are many top-level headers (3+), it's likely a slide deck, not a mind map
          if (topLevelHeaders.length >= 3) {
            return false;
          }
          
          if (contentString.match(/^#\s+.+$/m) || 
              (contentString.includes('# ') && contentString.split('\n').filter(l => l.trim().startsWith('#')).length >= 2)) {
            return true;
          }
        }
      } else if (typeof content === 'object' && content !== null) {
        parsed = content;
        if (parsed.task_type === 'mind_map') {
          return true;
        }
        // Also check if content field looks like a mind map
        if (parsed.content && typeof parsed.content === 'string') {
          const contentStr = parsed.content;
          
          // Exclude slide deck patterns
          const slidePattern = /(?:^#+\s+.*[Ss]lide\s+\d+|^#+\s+Slide\s+\d+)/m;
          if (slidePattern.test(contentStr)) {
            return false;
          }
          
          // Exclude infographic patterns
          const infographicKeywords = [
            /infographic/i,
            /visual\s+(?:elements?|brief|design)/i,
            /data\s+points?/i,
            /layout\s+(?:suggestions?|design)/i,
            /color\s+scheme/i,
          ];
          if (infographicKeywords.some(pattern => pattern.test(contentStr))) {
            return false; // This is likely an infographic, not a mind map
          }
          
          const lines = contentStr.split('\n');
          const topLevelHeaders = lines.filter(line => {
            const trimmed = line.trim();
            return trimmed.match(/^#{1,2}\s+/) && !trimmed.match(/^#{3,}/);
          });
          
          if (topLevelHeaders.length >= 3) {
            return false;
          }
          
          if (contentStr.match(/^#\s+.+$/m) || 
              (contentStr.includes('# ') && contentStr.split('\n').filter(l => l.trim().startsWith('#')).length >= 2)) {
            return true;
          }
        }
      }

      return false;
    } catch {
      return false;
    }
  };

  // Check if content is a report
  const isReportContent = (): boolean => {
    try {
      let parsed: any;
      
      if (typeof content === 'string') {
        try {
          parsed = JSON.parse(content);
          if (parsed.task_type === 'report') {
            return true;
          }
        } catch {
          // Not JSON, might be markdown report
        }
      } else if (typeof content === 'object' && content !== null) {
        parsed = content;
        if (parsed.task_type === 'report') {
          return true;
        }
      }

      return false;
    } catch {
      return false;
    }
  };

  // Check if content is an infographic brief
  const isInfographicContent = (): boolean => {
    try {
      let parsed: any;
      let contentString = '';
      
      if (typeof content === 'string') {
        contentString = content;
        try {
          parsed = JSON.parse(content);
          if (parsed.task_type === 'infographic') {
            return true;
          }
          // Check if content field contains infographic patterns
          if (parsed.content && typeof parsed.content === 'string') {
            contentString = parsed.content;
          }
        } catch {
          // Not JSON, might be markdown infographic brief
        }
      } else if (typeof content === 'object' && content !== null) {
        parsed = content;
        if (parsed.task_type === 'infographic') {
          return true;
        }
        // Check if content field contains infographic patterns
        if (parsed.content && typeof parsed.content === 'string') {
          contentString = parsed.content;
        }
      }

      // Check for infographic patterns in markdown
      if (contentString) {
        // Infographic briefs typically mention visual elements, data points, layout, color scheme
        const infographicKeywords = [
          /infographic/i,
          /visual\s+(?:elements?|brief|design)/i,
          /data\s+points?/i,
          /layout\s+(?:suggestions?|design)/i,
          /color\s+scheme/i,
          /visual\s+brief/i,
          /design\s+recommendations?/i,
        ];
        
        // Check if content contains infographic-specific keywords
        const hasInfographicKeywords = infographicKeywords.some(pattern => pattern.test(contentString));
        
        // Also check for section headers that might indicate infographic brief structure
        // Infographic briefs often have sections like "Visual Elements", "Data Points", "Layout", etc.
        const infographicSectionPatterns = [
          /^#+\s+.*visual\s+(?:elements?|brief)/im,
          /^#+\s+.*data\s+points?/im,
          /^#+\s+.*layout/im,
          /^#+\s+.*color\s+scheme/im,
        ];
        
        const hasInfographicSections = infographicSectionPatterns.some(pattern => pattern.test(contentString));
        
        if (hasInfographicKeywords || hasInfographicSections) {
          return true;
        }
      }

      return false;
    } catch {
      return false;
    }
  };

  // Check if content is a slide deck
  const isSlideDeckContent = (): boolean => {
    try {
      let parsed: any;
      let contentString = '';
      
      if (typeof content === 'string') {
        contentString = content;
        try {
          parsed = JSON.parse(content);
          if (parsed.task_type === 'slide_deck') {
            return true;
          }
          // Check if content field contains slide deck patterns
          if (parsed.content && typeof parsed.content === 'string') {
            contentString = parsed.content;
          }
        } catch {
          // Not JSON, might be markdown slide deck
        }
      } else if (typeof content === 'object' && content !== null) {
        parsed = content;
        if (parsed.task_type === 'slide_deck') {
          return true;
        }
        // Check if content field contains slide deck patterns
        if (parsed.content && typeof parsed.content === 'string') {
          contentString = parsed.content;
        }
      }

      // Check for slide deck patterns in markdown
      if (contentString) {
        // Look for patterns like "Slide 1", "Slide 2", etc. in headers
        const slidePattern = /(?:^#+\s+.*[Ss]lide\s+\d+|^#+\s+Slide\s+\d+)/m;
        if (slidePattern.test(contentString)) {
          return true;
        }
        
        // Look for multiple level 1 or 2 headers that might be slides
        // Slide decks typically have many top-level headers
        const lines = contentString.split('\n');
        const topLevelHeaders = lines.filter(line => {
          const trimmed = line.trim();
          return trimmed.match(/^#{1,2}\s+/) && !trimmed.match(/^#{3,}/);
        });
        
        // If there are 3+ top-level headers, it's likely a slide deck
        if (topLevelHeaders.length >= 3) {
          // Additional check: see if headers mention "slide" or have sequential numbering
          const hasSlideKeywords = topLevelHeaders.some(h => 
            /slide|presentation|deck/i.test(h)
          );
          const hasSequentialNumbers = topLevelHeaders.some(h => 
            /\d+/.test(h)
          );
          
          if (hasSlideKeywords || hasSequentialNumbers) {
            return true;
          }
        }
      }

      return false;
    } catch {
      return false;
    }
  };

  // Determine content type from content if not explicitly provided
  const detectContentType = (): ContentType => {
    if (contentType !== 'text') return contentType;
    
    if (typeof content === 'object' && content !== null) {
      return 'json';
    }
    
    if (typeof content === 'string') {
      // Check if it looks like markdown
      if (content.includes('```') || content.includes('# ') || content.includes('## ')) {
        return 'markdown';
      }
      // Check if it looks like JSON
      try {
        JSON.parse(content);
        return 'json';
      } catch {
        return 'text';
      }
    }
    
    return 'text';
  };

  const detectedType = detectContentType();
  const isQuiz = isQuizContent();
  const isFlashcards = isFlashcardsContent();
  // Check slide deck and infographic BEFORE mind map since they can also have headers
  const isSlideDeck = isSlideDeckContent();
  const isInfographic = isInfographicContent();
  const isMindMap = isMindMapContent();
  const isReport = isReportContent();

  // Format content for display
  const formatContent = (): string => {
    if (content === null || content === undefined) return '';
    
    if (typeof content === 'object') {
      return JSON.stringify(content, null, 2);
    }
    
    return String(content);
  };

  const displayContent = formatContent();

  // Handle copy to clipboard
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(displayContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      // Silently fail - user can try again
    }
  };

  // Handle save
  const handleSave = async () => {
    if (onSave && displayContent) {
      await onSave(displayContent);
    }
  };

  // Render content based on type
  const renderContent = () => {
    if (loading) {
      return (
        <div className="p-6 space-y-4">
          {/* Progress Indicator */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-text-secondary font-medium">
                {loadingType ? `Generating ${loadingType.replace('_', ' ')}` : 'Generating content'}
                {sourceCount ? ` (Processing ${sourceCount} ${sourceCount === 1 ? 'Source' : 'Sources'})` : ''}
              </span>
            </div>
            {/* Animated Indeterminate Progress Bar */}
            <div className="w-full h-2.5 bg-surface-subtle rounded-full overflow-hidden">
              <div className="h-full bg-accent-blue rounded-full animate-pulse" style={{ width: '60%' }} />
            </div>
          </div>
          <LoadingShimmer />
        </div>
      );
    }

    if (error) {
      return (
        <div className="p-6">
          <div className="flex items-start gap-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-semibold text-red-700 dark:text-red-300 mb-1">
                Generation Failed
              </p>
              <p className="text-sm text-red-600 dark:text-red-400 mb-3">
                {error}
              </p>
              <div className="flex items-center gap-3">
                {onRetry && (
                  <button
                    onClick={onRetry}
                    className="text-xs font-medium text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 px-3 py-1.5 rounded-md border border-red-300 dark:border-red-700 hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors flex items-center gap-1.5"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    Retry
                  </button>
                )}
                <button
                  onClick={onClose}
                  className="text-xs text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 underline cursor-pointer"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>
      );
    }

    if (!displayContent) {
      return (
        <div className="p-6">
          <p className="text-sm text-text-secondary text-center py-8">
            No content to display
          </p>
        </div>
      );
    }

    // Quiz content - render with QuizDisplay component
    if (isQuiz) {
      return (
        <div className="overflow-y-auto">
          <QuizDisplay quizData={content || displayContent} />
        </div>
      );
    }

    // Flashcards content - render with FlashcardsDisplay component
    if (isFlashcards) {
      return (
        <div className="overflow-y-auto">
          <FlashcardsDisplay flashcardsData={content || displayContent} />
        </div>
      );
    }

    // Slide Deck content - render with SlideDeckDisplay component
    // Check BEFORE mind map since slide decks can also have headers
    if (isSlideDeck) {
      return (
        <div className="h-full overflow-hidden">
          <SlideDeckDisplay slideData={content || displayContent} />
        </div>
      );
    }

    // Infographic content - render with InfographicBriefDisplay component
    // Check BEFORE mind map since infographics can also have headers
    if (isInfographic) {
      // For infographics, pass the raw content object to preserve image_url and other fields
      // If content is an object, use it directly; otherwise fall back to displayContent
      const infographicData = (typeof content === 'object' && content !== null) ? content : displayContent;
      return (
        <div className="overflow-y-auto">
          <InfographicBriefDisplay briefData={infographicData} />
        </div>
      );
    }

    // Mind Map content - render with MindMapDisplay component (full screen)
    if (isMindMap) {
      return (
        <div className="h-full overflow-hidden">
          <MindMapDisplay mindMapData={content || displayContent} />
        </div>
      );
    }

    // Report content - render with ReportDisplay component
    if (isReport) {
      return (
        <div className="overflow-y-auto">
          <ReportDisplay reportData={content || displayContent} />
        </div>
      );
    }

    // JSON content
    if (detectedType === 'json') {
      return (
        <div className="p-6">
          <div className="bg-surface-subtle rounded-xl border border-border-default p-4 overflow-x-auto">
            <pre className="text-sm text-text-primary font-mono whitespace-pre-wrap break-words">
              {displayContent}
            </pre>
          </div>
        </div>
      );
    }

    // Markdown content
    if (detectedType === 'markdown') {
      return (
        <div className="p-6">
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h1: ({ children, ...props }) => (
                  <h1 className="text-2xl font-bold text-text-primary mt-6 mb-3" {...props}>
                    {children}
                  </h1>
                ),
                h2: ({ children, ...props }) => (
                  <h2 className="text-xl font-semibold text-text-primary mt-5 mb-2" {...props}>
                    {children}
                  </h2>
                ),
                h3: ({ children, ...props }) => (
                  <h3 className="text-lg font-semibold text-text-primary mt-4 mb-2" {...props}>
                    {children}
                  </h3>
                ),
                p: ({ children, ...props }) => (
                  <p className="text-sm text-text-primary leading-relaxed mb-3" {...props}>
                    {children}
                  </p>
                ),
                ul: ({ children, ...props }) => (
                  <ul className="list-disc list-inside text-sm text-text-primary mb-3 space-y-1" {...props}>
                    {children}
                  </ul>
                ),
                ol: ({ children, ...props }) => (
                  <ol className="list-decimal list-inside text-sm text-text-primary mb-3 space-y-1" {...props}>
                    {children}
                  </ol>
                ),
                code: ({ children, ...props }) => (
                  <code className="bg-surface-hover px-1.5 py-0.5 rounded text-xs font-mono text-text-primary" {...props}>
                    {children}
                  </code>
                ),
                pre: ({ children, ...props }) => (
                  <pre className="bg-surface-subtle border border-border-default rounded-lg p-3 overflow-x-auto mb-3" {...props}>
                    {children}
                  </pre>
                ),
              }}
            >
              {displayContent}
            </ReactMarkdown>
          </div>
        </div>
      );
    }

    // Plain text content
    return (
      <div className="p-6">
        <div className="bg-surface-subtle rounded-xl border border-border-default p-4">
          <p className="text-sm text-text-primary leading-relaxed whitespace-pre-wrap break-words">
            {displayContent}
          </p>
        </div>
      </div>
    );
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
          aria-labelledby="generation-modal-title"
          aria-describedby="generation-modal-description"
          className={`bg-surface border border-border-default rounded-2xl shadow-2xl flex flex-col ${
            (isMindMap || isSlideDeck)
              ? 'w-full h-full max-w-[98vw] max-h-[98vh] m-2' 
              : 'w-full max-w-4xl max-h-[90vh]'
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-border-default">
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <div className="w-10 h-10 rounded-lg bg-accent-blue/10 flex items-center justify-center flex-shrink-0">
                {loading ? (
                  <Loader2 className="w-5 h-5 text-accent-blue animate-spin" />
                ) : error ? (
                  <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
                ) : (
                  <Download className="w-5 h-5 text-accent-blue" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <h2 id="generation-modal-title" className="text-lg font-bold text-text-primary">
                  {title}
                </h2>
                <p id="generation-modal-description" className="text-xs text-text-tertiary mt-0.5">
                  {loading
                    ? loadingType
                      ? `Generating ${loadingType.replace('_', ' ')}${sourceCount ? ` (Processing ${sourceCount} ${sourceCount === 1 ? 'Source' : 'Sources'})` : ''}...`
                      : 'Generating content...'
                    : error
                    ? 'Generation failed'
                    : isQuiz
                    ? 'Quiz Content'
                    : isFlashcards
                    ? 'Flashcards'
                    : isMindMap
                    ? 'Mind Map'
                    : isReport
                    ? 'Report'
                    : isInfographic
                    ? 'Infographic Brief'
                    : isSlideDeck
                    ? 'Slide Deck'
                    : detectedType === 'json'
                    ? 'JSON Content'
                    : detectedType === 'markdown'
                    ? 'Markdown Content'
                    : 'Text Content'}
                </p>
                {/* Custom Instructions Display */}
                {customInstructions && customInstructions.trim() && (
                  <div className="mt-2 p-2 bg-surface-subtle border border-border-default rounded-md">
                    <p className="text-xs font-medium text-text-secondary mb-1">Custom Instructions:</p>
                    <p className="text-xs text-text-primary italic">{customInstructions}</p>
                  </div>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {/* Copy Button */}
              {!loading && !error && displayContent && (
                <button
                  onClick={handleCopy}
                  className="p-2 rounded-lg hover:bg-surface-hover transition-colors text-text-secondary hover:text-text-primary"
                  aria-label="Copy to clipboard"
                  title="Copy to clipboard"
                >
                  {copied ? (
                    <Check className="w-5 h-5 text-accent-green" />
                  ) : (
                    <Copy className="w-5 h-5" />
                  )}
                </button>
              )}
              {/* Close Button */}
              <button
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-surface-hover transition-colors text-text-secondary hover:text-text-primary"
                aria-label="Close modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className={`flex-1 ${(isMindMap || isSlideDeck) ? 'overflow-hidden' : 'overflow-y-auto'}`}>
            {renderContent()}
          </div>

          {/* Footer */}
          <div className="p-6 border-t border-border-default flex justify-end gap-3">
            <Button
              variant="secondary"
              onClick={onClose}
              disabled={loading}
            >
              Close
            </Button>
            {!loading && !error && displayContent && onSave && (
              <Button
                variant="primary"
                onClick={handleSave}
              >
                Save
              </Button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
