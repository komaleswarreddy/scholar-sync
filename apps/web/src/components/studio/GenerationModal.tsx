/**
 * Generation Modal — unified viewer for studio assets (generate + preview).
 */

'use client';

import { useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  X,
  Loader2,
  AlertCircle,
  Copy,
  Check,
  RotateCcw,
  Sparkles,
  Network,
  Presentation,
  Layers,
  HelpCircle,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { QuizDisplay } from './QuizDisplay';
import { FlashcardsDisplay } from './FlashcardsDisplay';
import { MindMapDisplay } from './MindMapDisplay';
import { SlideDeckDisplay } from './SlideDeckDisplay';
import {
  isFullscreenStudioType,
  resolveStudioDisplayKind,
  type StudioDisplayKind,
} from '@/lib/studio-display';

export type ContentType = 'json' | 'markdown' | 'text';

interface GenerationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave?: () => void | Promise<void>;
  onRetry?: () => void | Promise<void>;
  title?: string;
  studioType?: string;
  contentType?: ContentType;
  content?: string | object | null;
  loading?: boolean;
  loadingType?: string;
  sourceCount?: number;
  customInstructions?: string;
  error?: string | null;
}

const KIND_LABELS: Record<StudioDisplayKind, string> = {
  quiz: 'Quiz',
  flashcards: 'Flashcards',
  mind_map: 'Mind Map',
  slide_deck: 'Slide Deck',
  json: 'JSON Content',
  markdown: 'Markdown Content',
  text: 'Text Content',
};

const TYPE_ICONS: Record<string, typeof Sparkles> = {
  quiz: HelpCircle,
  flashcards: Layers,
  mind_map: Network,
  slide_deck: Presentation,
};

function formatDisplayContent(content: string | object | null | undefined): string {
  if (content === null || content === undefined) return '';
  if (typeof content === 'object') return JSON.stringify(content, null, 2);
  return String(content);
}

function humanizeType(type?: string): string {
  if (!type) return 'content';
  return type.replace(/_/g, ' ');
}

function LoadingProgress({ wide = false }: { wide?: boolean }) {
  return (
    <div className={`w-full space-y-3 ${wide ? 'max-w-md' : 'max-w-sm'}`}>
      <div className="w-full h-2 bg-[var(--color-brand-surface)] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-[var(--color-brand-primary)] animate-pulse"
          style={{ width: '62%' }}
        />
      </div>
      <p className="text-xs text-[var(--color-home-label)] text-center flex items-center justify-center gap-2">
        <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" />
        <span>Generating…</span>
      </p>
    </div>
  );
}

export function GenerationModal({
  isOpen,
  onClose,
  onSave,
  onRetry,
  title = 'Generated Content',
  studioType,
  contentType = 'text',
  content = null,
  loading = false,
  loadingType,
  sourceCount,
  customInstructions,
  error = null,
}: GenerationModalProps) {
  const [copied, setCopied] = useState(false);

  const activeType = loading ? loadingType ?? studioType : studioType;
  const displayKind = useMemo(
    () => resolveStudioDisplayKind(activeType, content),
    [activeType, content],
  );
  const isFullscreen = isFullscreenStudioType(activeType, displayKind);
  const displayContent = formatDisplayContent(content);
  const hasContent = displayContent.length > 0;
  const TypeIcon = TYPE_ICONS[activeType ?? ''] ?? Sparkles;

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  useEffect(() => {
    setCopied(false);
  }, [content]);

  if (!isOpen) return null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(displayContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  const loadingLabel = loadingType
    ? `Generating ${humanizeType(loadingType)}`
    : 'Generating content';

  const sourceLine = sourceCount
    ? `Processing ${sourceCount} ${sourceCount === 1 ? 'source' : 'sources'}…`
    : 'Building your interactive view…';

  const renderBrandedLoading = (opts: {
    headline: string;
    description: ReactNode;
    icon: typeof Sparkles;
    fullscreen?: boolean;
  }) => {
    const Icon = opts.icon;
    return (
      <div
        className={`studio-modal-loading ${opts.fullscreen ? 'studio-modal-loading--fullscreen' : ''}`}
      >
        <div className="mb-6 w-20 h-20 rounded-2xl bg-[var(--color-brand-surface)] flex items-center justify-center border border-[var(--color-home-border)]">
          <Icon className="w-9 h-9 text-[var(--color-brand-text)] animate-pulse" />
        </div>
        <h3 className="text-lg font-semibold text-[var(--color-home-text)] text-center mb-2">
          {opts.headline}
        </h3>
        <div className="text-sm text-[var(--color-home-text-muted)] text-center max-w-md leading-relaxed mb-8">
          {opts.description}
        </div>
        <LoadingProgress wide={opts.fullscreen} />
      </div>
    );
  };

  const renderLoading = () => {
    if (loadingType === 'quiz') {
      return renderBrandedLoading({
        icon: HelpCircle,
        headline: 'Creating your quiz',
        description: (
          <>
            We&apos;re writing questions tailored to your choices, using your selected sources.
            {sourceCount ? (
              <span className="block mt-1">
                Reading from {sourceCount} {sourceCount === 1 ? 'source' : 'sources'}…
              </span>
            ) : null}
          </>
        ),
      });
    }

    if (isFullscreen) {
      const icon = loadingType === 'slide_deck' ? Presentation : Network;
      return renderBrandedLoading({
        icon,
        fullscreen: true,
        headline: loadingLabel,
        description: sourceLine,
      });
    }

    const icon = TYPE_ICONS[loadingType ?? ''] ?? Sparkles;
    const headline =
      loadingType === 'flashcards'
        ? 'Creating flashcards'
        : loadingLabel;

    return renderBrandedLoading({
      icon,
      headline,
      description: sourceLine,
    });
  };

  const renderBody = () => {
    if (loading) return renderLoading();

    if (error) {
      return (
        <div className="p-6">
          <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-xl">
            <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-semibold text-red-700 mb-1">Generation Failed</p>
              <p className="text-sm text-red-600 mb-3">{error}</p>
              <div className="flex items-center gap-3">
                {onRetry && (
                  <button
                    type="button"
                    onClick={onRetry}
                    className="text-xs font-medium text-red-600 hover:text-red-800 px-3 py-1.5 rounded-md border border-red-300 hover:bg-red-100 transition-colors flex items-center gap-1.5"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    Retry
                  </button>
                )}
                <button type="button" onClick={onClose} className="text-xs text-red-600 underline">
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        </div>
      );
    }

    if (!hasContent) {
      return (
        <div className="p-6">
          <p className="text-sm text-[var(--color-home-text-muted)] text-center py-8">
            No content to display
          </p>
        </div>
      );
    }

    switch (displayKind) {
      case 'quiz':
        return (
          <div className="overflow-y-auto flex-1">
            <QuizDisplay quizData={content ?? displayContent} />
          </div>
        );
      case 'flashcards':
        return (
          <div className="overflow-y-auto flex-1">
            <FlashcardsDisplay flashcardsData={content ?? displayContent} />
          </div>
        );
      case 'slide_deck':
        return (
          <div className="flex-1 min-h-0 overflow-hidden">
            <SlideDeckDisplay slideData={content ?? displayContent} />
          </div>
        );
      case 'mind_map':
        return (
          <div className="flex-1 min-h-0 overflow-hidden">
            <MindMapDisplay mindMapData={content ?? displayContent} filename={title} />
          </div>
        );
      case 'json':
        return (
          <div className="p-6 overflow-y-auto flex-1">
            <div className="bg-[var(--color-brand-surface)] rounded-xl border border-[var(--color-home-border)] p-4 overflow-x-auto">
              <pre className="text-sm text-[var(--color-home-text)] font-mono whitespace-pre-wrap break-words">
                {displayContent}
              </pre>
            </div>
          </div>
        );
      case 'markdown':
        return (
          <div className="p-6 overflow-y-auto flex-1">
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{displayContent}</ReactMarkdown>
            </div>
          </div>
        );
      default:
        return (
          <div className="p-6 overflow-y-auto flex-1">
            <div className="bg-[var(--color-brand-surface)] rounded-xl border border-[var(--color-home-border)] p-4">
              <p className="text-sm text-[var(--color-home-text)] leading-relaxed whitespace-pre-wrap break-words">
                {displayContent}
              </p>
            </div>
          </div>
        );
    }
  };

  const subtitle = loading
    ? loadingType === 'quiz'
      ? 'Hang tight — almost there.'
      : `${loadingLabel}${sourceCount ? ` (${sourceCount} ${sourceCount === 1 ? 'source' : 'sources'})` : ''}…`
    : error
      ? 'Generation failed'
      : KIND_LABELS[displayKind] ?? (contentType !== 'text' ? contentType : 'Content');

  return (
    <>
      <div
        className="assets-modal-backdrop"
        onClick={onClose}
        role="presentation"
        aria-hidden="true"
      />

      <div
        className={`studio-modal-host ${isFullscreen ? 'studio-modal-host--fullscreen' : ''}`}
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="generation-modal-title"
          className={`assets-modal shadow-2xl ${
            isFullscreen ? 'assets-modal--fullscreen' : 'assets-modal--studio'
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="assets-modal__header flex items-center justify-between gap-3 px-5 py-4 border-b border-[var(--color-home-border)]">
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <div className="w-10 h-10 rounded-lg bg-[var(--color-brand-surface)] flex items-center justify-center flex-shrink-0">
                {loading ? (
                  <Loader2 className="w-5 h-5 text-[var(--color-brand-text)] animate-spin" />
                ) : error ? (
                  <AlertCircle className="w-5 h-5 text-red-600" />
                ) : (
                  <TypeIcon className="w-5 h-5 text-[var(--color-brand-text)]" />
                )}
              </div>
              <div className="min-w-0 flex-1">
                <h2 id="generation-modal-title" className="assets-modal__title truncate">
                  {title}
                </h2>
                <p className="text-xs text-[var(--color-home-text-muted)] mt-0.5">{subtitle}</p>
                {!loading && customInstructions?.trim() && (
                  <p className="text-[11px] text-[var(--color-home-label)] mt-1 italic truncate">
                    {customInstructions}
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-1 flex-shrink-0">
              {!loading && !error && hasContent && (
                <button
                  type="button"
                  onClick={handleCopy}
                  className="p-2 rounded-lg hover:bg-[var(--color-brand-surface)] text-[var(--color-home-label)]"
                  aria-label="Copy to clipboard"
                  title="Copy to clipboard"
                >
                  {copied ? (
                    <Check className="w-5 h-5 text-[var(--color-brand-text)]" />
                  ) : (
                    <Copy className="w-5 h-5" />
                  )}
                </button>
              )}
              <button
                type="button"
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-[var(--color-brand-surface)] text-[var(--color-home-label)]"
                aria-label="Close modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          <div
            className={`assets-modal__body ${
              isFullscreen ? 'assets-modal__body--fill' : 'assets-modal__body--scroll'
            }`}
          >
            {renderBody()}
          </div>

          <div className="assets-modal__footer px-5 py-4 border-t border-[var(--color-home-border)] flex justify-end gap-3">
            <button type="button" className="profile-btn-secondary" onClick={onClose}>
              Close
            </button>
            {!loading && !error && hasContent && onSave && (
              <button type="button" className="profile-btn-primary" onClick={onSave}>
                Save
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
