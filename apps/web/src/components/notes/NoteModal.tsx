/**
 * Note Modal Component
 * 
 * Modal for viewing and editing notes, similar to GenerationModal.
 * Supports editing, saving, and discarding changes.
 */

'use client';

import { useEffect, useState, useRef } from 'react';
import { X, FileText, Save, Check } from 'lucide-react';
import { Button } from '../ui/Button';

interface NoteModalProps {
  isOpen: boolean;
  onClose: () => void;
  noteId: string | null;
  initialContent: string;
  onSave: (content: string) => Promise<void>;
  onDiscard?: () => void;
  title?: string;
  isSaving?: boolean;
  error?: string | null;
}

export function NoteModal({
  isOpen,
  onClose,
  noteId,
  initialContent,
  onSave,
  onDiscard,
  title = 'Note',
  isSaving = false,
  error = null,
}: NoteModalProps) {
  const [content, setContent] = useState(initialContent);
  const [hasChanges, setHasChanges] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Update content when initialContent changes (e.g., when switching notes)
  useEffect(() => {
    if (isOpen) {
      setContent(initialContent);
      setHasChanges(false);
      // Focus textarea when modal opens
      if (textareaRef.current) {
        setTimeout(() => {
          textareaRef.current?.focus();
          const len = textareaRef.current?.value.length || 0;
          textareaRef.current?.setSelectionRange(len, len);
        }, 100);
      }
    }
  }, [initialContent, isOpen]);

  // Close modal on Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        if (hasChanges) {
          const confirmed = window.confirm('You have unsaved changes. Are you sure you want to close?');
          if (!confirmed) return;
        }
        setContent(initialContent);
        setHasChanges(false);
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
  }, [isOpen, hasChanges, initialContent, onClose]);

  const handleClose = () => {
    if (hasChanges) {
      const confirmed = window.confirm('You have unsaved changes. Are you sure you want to close?');
      if (!confirmed) return;
    }
    setContent(initialContent);
    setHasChanges(false);
    onClose();
  };

  const handleContentChange = (newContent: string) => {
    setContent(newContent);
    setHasChanges(newContent !== initialContent);
  };

  const handleSave = async () => {
    try {
      await onSave(content.trim());
      setHasChanges(false);
      onClose();
    } catch (err) {
      // Error is handled by parent component
      console.error('Failed to save note:', err);
    }
  };

  const handleDiscard = () => {
    if (hasChanges) {
      const confirmed = window.confirm('You have unsaved changes. Are you sure you want to discard them?');
      if (!confirmed) return;
    }
    setContent(initialContent);
    setHasChanges(false);
    if (onDiscard) {
      onDiscard();
    } else {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 backdrop-blur-sm"
        onClick={handleClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="note-modal-title"
          className="bg-surface border border-border-default rounded-2xl shadow-2xl flex flex-col w-full max-w-4xl max-h-[90vh]"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-border-default">
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <div className="w-10 h-10 rounded-lg bg-accent-blue/10 flex items-center justify-center flex-shrink-0">
                <FileText className="w-5 h-5 text-accent-blue" />
              </div>
              <div className="flex-1 min-w-0">
                <h2 id="note-modal-title" className="text-lg font-bold text-text-primary">
                  {title}
                </h2>
                {hasChanges && (
                  <p className="text-xs text-text-tertiary mt-0.5">
                    Unsaved changes
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {/* Close Button */}
              <button
                onClick={handleClose}
                className="p-2 rounded-lg hover:bg-surface-hover transition-colors text-text-secondary hover:text-text-primary"
                aria-label="Close modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto">
            {error ? (
              <div className="p-6">
                <div className="flex items-start gap-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-red-700 dark:text-red-300 mb-1">
                      Error
                    </p>
                    <p className="text-sm text-red-600 dark:text-red-400">
                      {error}
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-6">
                <textarea
                  ref={textareaRef}
                  value={content}
                  onChange={(e) => handleContentChange(e.target.value)}
                  onKeyDown={(e) => {
                    // Ctrl/Cmd + S to save
                    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                      e.preventDefault();
                      handleSave();
                    }
                  }}
                  placeholder="Start typing your note..."
                  className="w-full h-full min-h-[400px] resize-none bg-transparent text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-0 border-0 p-0 font-mono text-sm leading-relaxed"
                  style={{
                    maxHeight: 'calc(90vh - 300px)',
                    overflowY: 'auto',
                  }}
                />
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="p-6 border-t border-border-default flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="text-xs text-text-tertiary">
                {content.length.toLocaleString()} {content.length === 1 ? 'character' : 'characters'}
              </span>
              <span className="text-xs text-text-tertiary">
                Press Ctrl+S to save, Esc to close
              </span>
            </div>
            <div className="flex items-center gap-3">
              <Button
                variant="secondary"
                onClick={handleDiscard}
                disabled={isSaving}
              >
                Discard
              </Button>
              <Button
                variant="primary"
                onClick={handleSave}
                disabled={isSaving || !content.trim() || !hasChanges}
                className="bg-accent-blue text-background hover:opacity-90"
              >
                {isSaving ? (
                  <>
                    <Save className="w-4 h-4 mr-1" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4 mr-1" />
                    Save
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
