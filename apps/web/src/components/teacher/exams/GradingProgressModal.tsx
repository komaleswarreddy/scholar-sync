'use client';

import { useEffect } from 'react';
import { Loader2 } from 'lucide-react';

interface GradingProgressModalProps {
  open: boolean;
  progress: number;
  onComplete: () => void;
}

export function GradingProgressModal({ open, progress, onComplete }: GradingProgressModalProps) {
  useEffect(() => {
    if (open && progress >= 100) {
      const timer = setTimeout(onComplete, 400);
      return () => clearTimeout(timer);
    }
  }, [open, progress, onComplete]);

  if (!open) return null;

  return (
    <div className="teacher-exam-modal-overlay teacher-exam-modal-overlay--grading" role="dialog" aria-modal="true">
      <div className="teacher-exam-grading-modal">
        <Loader2 className="h-10 w-10 teacher-exam-grading-modal__spinner" />
        <h3 className="teacher-exam-grading-modal__title">Grading exam…</h3>
        <p className="teacher-exam-grading-modal__subtitle">
          Processing OMR sheets and calculating scores
        </p>
        <div className="teacher-exam-grading-modal__bar">
          <div
            className="teacher-exam-grading-modal__fill"
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>
        <p className="teacher-exam-grading-modal__percent">{Math.round(progress)}%</p>
      </div>
    </div>
  );
}
