/**
 * Note Modal — create/edit notebook notes (assets-modal chrome).
 */

'use client';

import { useEffect, useState, useRef } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { TOAST_MIN_VISIBLE_MS, useAppToast } from '@/contexts/AppToastContext';

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
  const [mounted, setMounted] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { showToast } = useAppToast();
  const isNewNote = !noteId;

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (isOpen) {
      setContent(initialContent);
      setHasChanges(false);
      if (textareaRef.current) {
        setTimeout(() => {
          textareaRef.current?.focus();
          const len = textareaRef.current?.value.length || 0;
          textareaRef.current?.setSelectionRange(len, len);
        }, 100);
      }
    }
  }, [initialContent, isOpen]);

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
      await showToast(isNewNote ? 'Note created' : 'Note saved', {
        minVisibleMs: TOAST_MIN_VISIBLE_MS,
      });
    } catch (err) {
      console.error('Failed to save note:', err);
      showToast('Could not save note');
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

  if (!isOpen || !mounted) return null;

  const canSave = content.trim().length > 0 && (isNewNote || hasChanges);

  return createPortal(
    <div className="assets-modal-backdrop" role="presentation" onClick={handleClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="note-modal-title"
        className="assets-modal assets-modal--note"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="min-w-0">
            <h2 id="note-modal-title" className="assets-modal__title">
              {isNewNote ? 'New note' : title}
            </h2>
            <p className="text-[13px] text-[var(--color-home-text-muted)] mt-1">
              {isNewNote
                ? 'Capture ideas, summaries, or questions for this notebook.'
                : hasChanges
                  ? 'Unsaved changes'
                  : 'Edit your note'}
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="p-1 rounded-md text-[var(--color-home-label)] hover:bg-[var(--color-brand-surface)] flex-shrink-0"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error ? (
          <p className="text-[13px] text-red-600 mb-3">{error}</p>
        ) : null}

        <label className="profile-field-label" htmlFor="note-modal-content">
          Note
        </label>
        <textarea
          id="note-modal-content"
          ref={textareaRef}
          value={content}
          onChange={(e) => handleContentChange(e.target.value)}
          onKeyDown={(e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
              e.preventDefault();
              if (canSave && !isSaving) handleSave();
            }
          }}
          placeholder="Start typing your note..."
          className="library-search-input w-full px-4 py-3 text-[14px] mt-1 min-h-[280px] resize-y leading-relaxed"
        />

        <p className="text-[11px] text-[var(--color-home-label)] mt-2">
          {content.length.toLocaleString()} characters · Ctrl+S to save
        </p>

        <div className="flex flex-wrap justify-end gap-2 mt-4 pt-4 border-t border-[var(--color-home-border)]">
          <button type="button" className="profile-btn-secondary" onClick={handleDiscard} disabled={isSaving}>
            Cancel
          </button>
          <button
            type="button"
            className="profile-btn-primary"
            onClick={handleSave}
            disabled={isSaving || !canSave}
          >
            {isSaving ? 'Saving...' : isNewNote ? 'Create note' : 'Save note'}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
