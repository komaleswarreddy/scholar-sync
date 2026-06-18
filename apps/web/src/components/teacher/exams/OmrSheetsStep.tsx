'use client';

import { useMemo, useState } from 'react';
import { Download } from 'lucide-react';
import { buildMockOmrRows } from '@/lib/teacher-exam-mock-data';
import type { ExamWizardDraft, OmrStudentRow } from '@/lib/teacher-exam-types';
import { ExamFileDropzone } from './ExamFileDropzone';
import { GradingProgressModal } from './GradingProgressModal';
import { OmrStudentRowComponent } from './OmrStudentRow';
import { TagStudentModal } from './TagStudentModal';

interface OmrSheetsStepProps {
  draft: ExamWizardDraft;
  onChange: (patch: Partial<ExamWizardDraft>) => void;
  onFinish: () => void;
}

export function OmrSheetsStep({ draft, onChange, onFinish }: OmrSheetsStepProps) {
  const [tagRowId, setTagRowId] = useState<string | null>(null);
  const [grading, setGrading] = useState(false);
  const [progress, setProgress] = useState(0);

  const rows = draft.omrRows.length > 0 ? draft.omrRows : [];

  const summary = useMemo(() => {
    const matched = rows.filter(
      (r) => r.status === 'matched' || r.status === 'confirmed' || r.status === 'tagged_manual',
    ).length;
    const attention = rows.filter(
      (r) => r.status === 'unknown_likely' || r.status === 'multiple_marks',
    ).length;
    const unmatched = rows.filter((r) => r.status === 'unmatched').length;
    return { total: rows.length, matched, attention, unmatched };
  }, [rows]);

  const handleUpload = () => {
    const omrRows = buildMockOmrRows();
    onChange({
      omrUploaded: true,
      omrFileCount: omrRows.length,
      omrRows,
    });
  };

  const updateRow = (id: string, patch: Partial<OmrStudentRow>) => {
    onChange({
      omrRows: rows.map((r) => (r.id === id ? { ...r, ...patch } : r)),
    });
  };

  const handleFinish = () => {
    setGrading(true);
    setProgress(0);
    let p = 0;
    const interval = setInterval(() => {
      p += 12;
      setProgress(p);
      if (p >= 100) {
        clearInterval(interval);
      }
    }, 120);
  };

  return (
    <div className="teacher-exam-step teacher-exam-step--wide">
      <h2 className="teacher-exam-step__title">OMR sheets</h2>
      <p className="teacher-exam-step__subtitle">
        Upload scanned OMR sheets for automatic grading.
      </p>

      <div className="teacher-exam-omr-banner">
        <p className="teacher-exam-omr-banner__text">
          Use the Syllabus.ai OMR template only for best results.
        </p>
        <button type="button" className="teacher-exam-omr-banner__link">
          <Download className="h-4 w-4" />
          Download template
        </button>
      </div>

      {!draft.omrUploaded ? (
        <ExamFileDropzone
          accept=".pdf,.png,.jpg,.jpeg,.zip"
          hint="Drop OMR sheets here"
          subhint="PDF, images, or ZIP · Max 50 MB"
          onFileSelect={() => handleUpload()}
        />
      ) : (
        <>
          <p className="teacher-exam-omr-summary">
            {summary.total} sheets · {summary.matched} matched · {summary.attention} need
            attention · {summary.unmatched} unmatched
          </p>

          <div className="teacher-exam-omr-list">
            {rows.map((row) => (
              <OmrStudentRowComponent
                key={row.id}
                row={row}
                onConfirm={() => {
                  if (row.likelyRoll && row.likelyName) {
                    updateRow(row.id, {
                      status: 'confirmed',
                      rollNumber: row.likelyRoll,
                      name: row.likelyName,
                      displayLabel: `Roll ${row.likelyRoll} - ${row.likelyName}`,
                      message: '20 of 20 questions read',
                    });
                  }
                }}
                onPickDifferent={() => setTagRowId(row.id)}
                onEditResponses={() => {
                  updateRow(row.id, {
                    message: 'Responses updated manually',
                    status: 'matched',
                  });
                }}
                onTagManually={() => setTagRowId(row.id)}
              />
            ))}
          </div>
        </>
      )}

      <TagStudentModal
        open={!!tagRowId}
        onClose={() => setTagRowId(null)}
        onSave={(rollNumber) => {
          if (!tagRowId) return;
          updateRow(tagRowId, {
            status: 'tagged_manual',
            rollNumber,
            name: 'Manual Tagged Student',
            displayLabel: `Roll ${rollNumber} - Manual Tagged Student`,
            message: 'Tagged manually',
          });
          setTagRowId(null);
        }}
      />

      <GradingProgressModal
        open={grading}
        progress={progress}
        onComplete={() => {
          setGrading(false);
          onFinish();
        }}
      />

      {draft.omrUploaded && !grading && (
        <div className="teacher-exam-concept-actions">
          <button type="button" className="teacher-exam-concept-actions__approve" onClick={handleFinish}>
            Finish and grade
          </button>
        </div>
      )}
    </div>
  );
}
