'use client';

import { X } from 'lucide-react';
import { VERIFICATION_DISCLAIMER } from '@/lib/analytics-prep-mock-data';

type VerificationLearnModalProps = {
  open: boolean;
  onClose: () => void;
};

export function VerificationLearnModal({ open, onClose }: VerificationLearnModalProps) {
  if (!open) return null;

  return (
    <div className="assets-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="assets-modal prep-verification-modal"
        role="dialog"
        aria-labelledby="verification-modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 mb-4">
          <h2 id="verification-modal-title" className="text-[18px] font-bold text-[var(--color-home-text)]">
            {VERIFICATION_DISCLAIMER.title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-md hover:bg-[var(--color-brand-surface)]"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <p className="text-[14px] text-[var(--color-home-text-muted)] leading-relaxed whitespace-pre-line">
          {VERIFICATION_DISCLAIMER.body}
        </p>
        <button type="button" onClick={onClose} className="profile-btn-primary mt-6 w-full sm:w-auto">
          Got it
        </button>
      </div>
    </div>
  );
}
