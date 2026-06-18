'use client';

import type { OmrStudentRow as OmrRow } from '@/lib/teacher-exam-types';

interface OmrStudentRowProps {
  row: OmrRow;
  onConfirm?: () => void;
  onPickDifferent?: () => void;
  onEditResponses?: () => void;
  onTagManually?: () => void;
}

function StatusDot({ status }: { status: OmrRow['status'] }) {
  const className =
    status === 'matched' || status === 'confirmed' || status === 'tagged_manual'
      ? 'teacher-exam-omr-row__dot--green'
      : status === 'multiple_marks' || status === 'unknown_likely'
        ? 'teacher-exam-omr-row__dot--orange'
        : 'teacher-exam-omr-row__dot--red';

  return <span className={`teacher-exam-omr-row__dot ${className}`} aria-hidden />;
}

export function OmrStudentRowComponent({
  row,
  onConfirm,
  onPickDifferent,
  onEditResponses,
  onTagManually,
}: OmrStudentRowProps) {
  return (
    <div className="teacher-exam-omr-row">
      <StatusDot status={row.status} />
      <div className="teacher-exam-omr-row__info">
        <p className="teacher-exam-omr-row__label">{row.displayLabel}</p>
        <p className="teacher-exam-omr-row__message">{row.message}</p>
      </div>
      <div className="teacher-exam-omr-row__actions">
        {row.status === 'unknown_likely' && (
          <>
            <button type="button" className="teacher-exam-omr-row__btn" onClick={onConfirm}>
              Confirm
            </button>
            <button
              type="button"
              className="teacher-exam-omr-row__btn teacher-exam-omr-row__btn--ghost"
              onClick={onPickDifferent}
            >
              Pick different
            </button>
          </>
        )}
        {row.status === 'multiple_marks' && (
          <button type="button" className="teacher-exam-omr-row__btn" onClick={onEditResponses}>
            Edit responses
          </button>
        )}
        {row.status === 'unmatched' && (
          <button type="button" className="teacher-exam-omr-row__btn" onClick={onTagManually}>
            Tag manually
          </button>
        )}
      </div>
    </div>
  );
}
