'use client';

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Loader2, X } from 'lucide-react';

/** Backend requires non-empty trimmed reason; keep UX low-friction. */
const MIN_REASON_LENGTH = 3;

type NotebookDislikeReasonModalProps = {
  open: boolean;
  onClose: () => void;
  onSubmit: (reason: string) => Promise<void>;
};

export function NotebookDislikeReasonModal({
  open,
  onClose,
  onSubmit,
}: NotebookDislikeReasonModalProps) {
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!open) {
      setReason('');
      setError(null);
      setSubmitting(false);
    }
  }, [open]);

  if (!open || !mounted) return null;

  const trimmed = reason.trim();
  const charsRemaining = Math.max(0, MIN_REASON_LENGTH - trimmed.length);
  const canSubmit = trimmed.length >= MIN_REASON_LENGTH && !submitting;

  const handleSubmit = async () => {
    if (trimmed.length < MIN_REASON_LENGTH) {
      setError(`Please enter at least ${MIN_REASON_LENGTH} characters.`);
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit(trimmed);
      onClose();
    } catch {
      setError('Could not save feedback. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return createPortal(
    <div
      className="notebook-dislike-modal-overlay"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="notebook-dislike-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="notebook-dislike-title"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="notebook-dislike-modal-header">
          <h2 id="notebook-dislike-title" className="notebook-dislike-modal-title">
            What went wrong?
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="notebook-dislike-modal-close"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="notebook-dislike-modal-body">
          <p className="notebook-dislike-modal-description">
            Briefly describe what was wrong with this response so we can improve future answers.
          </p>
          <textarea
            value={reason}
            onChange={(e) => {
              setReason(e.target.value);
              if (error) setError(null);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                void handleSubmit();
              }
            }}
            rows={4}
            placeholder="e.g. The answer was incorrect or missed important details..."
            className="notebook-dislike-modal-input"
            autoFocus
          />
          <div className="notebook-dislike-modal-meta">
            {error ? (
              <p className="notebook-dislike-modal-error">{error}</p>
            ) : charsRemaining > 0 ? (
              <p className="notebook-dislike-modal-hint">
                {charsRemaining} more character{charsRemaining === 1 ? '' : 's'} needed
              </p>
            ) : (
              <p className="notebook-dislike-modal-hint notebook-dislike-modal-hint--ready">
                Ready to submit
              </p>
            )}
          </div>
        </div>

        <div className="notebook-dislike-modal-footer">
          <button
            type="button"
            onClick={onClose}
            className="notebook-dislike-modal-btn notebook-dislike-modal-btn--ghost"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void handleSubmit()}
            disabled={submitting}
            className={`notebook-dislike-modal-btn notebook-dislike-modal-btn--primary${
              canSubmit ? '' : ' notebook-dislike-modal-btn--primary-muted'
            }`}
          >
            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Submit feedback'}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
