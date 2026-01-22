'use client';

import { useState, useEffect } from 'react';
import { Save, X, Trash2 } from 'lucide-react';
import { Button } from '../ui/Button';
import { apiClient } from '@/lib/api-client';

interface DraftSaveModalProps {
  isOpen: boolean;
  draftContent: string;
  onSave: () => void;
  onDiscard: () => void;
  onCancel: () => void;
}

export function DraftSaveModal({
  isOpen,
  draftContent,
  onSave,
  onDiscard,
  onCancel,
}: DraftSaveModalProps) {
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Reset state when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setSaveError(null);
      setIsSaving(false);
    }
  }, [isOpen]);

  // Handle Escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onCancel();
      }
    };

    document.addEventListener('keydown', handleEscape);
    // Prevent body scroll when modal is open
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onCancel]);

  const handleSaveToNote = async () => {
    if (!draftContent.trim()) {
      setSaveError('Draft content is empty');
      return;
    }

    setIsSaving(true);
    setSaveError(null);

    try {
      await apiClient.createNote(draftContent.trim());
      // Trigger note created event to refresh notes list
      window.dispatchEvent(new Event('noteCreated'));
      onSave();
    } catch (error: any) {
      console.error('Failed to save draft as note:', error);
      const errorMessage = error?.message || error?.apiError?.message || 'Failed to save note. Please try again.';
      setSaveError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  const preview = draftContent.length > 200 
    ? draftContent.substring(0, 200) + '...' 
    : draftContent;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-50 backdrop-blur-sm"
        onClick={onCancel}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="draft-modal-title"
          className="bg-surface border border-border-default rounded-2xl shadow-2xl w-full max-w-md flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-border-default">
            <h2
              id="draft-modal-title"
              className="text-lg font-semibold text-text-primary"
            >
              Unsaved Note Draft
            </h2>
            <button
              onClick={onCancel}
              className="p-1 rounded-lg hover:bg-surface-hover text-text-secondary hover:text-text-primary transition-colors"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6 flex-1 overflow-y-auto">
            <p className="text-sm text-text-secondary mb-4">
              You have an unsaved note draft. What would you like to do?
            </p>
            
            {/* Draft Preview */}
            <div className="bg-surface-subtle border border-border-default rounded-lg p-4 mb-4 max-h-48 overflow-y-auto">
              <p className="text-sm text-text-primary whitespace-pre-wrap font-mono">
                {preview}
              </p>
            </div>

            {/* Error Message */}
            {saveError && (
              <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                <p className="text-xs text-red-400">{saveError}</p>
              </div>
            )}
          </div>

          {/* Footer Actions */}
          <div className="p-6 border-t border-border-default flex items-center justify-end gap-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={onCancel}
              disabled={isSaving}
              className="text-text-secondary hover:text-text-primary"
            >
              Cancel
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onDiscard}
              disabled={isSaving}
              className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
            >
              <Trash2 className="w-4 h-4 mr-1" />
              Discard
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleSaveToNote}
              disabled={isSaving || !draftContent.trim()}
              className="bg-accent-blue text-background hover:opacity-90"
            >
              <Save className="w-4 h-4 mr-1" />
              {isSaving ? 'Saving...' : 'Save to Note'}
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}
