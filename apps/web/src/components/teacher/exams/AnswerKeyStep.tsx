'use client';

import { CheckCircle2 } from 'lucide-react';
import type { AnswerChoice, ExamWizardDraft } from '@/lib/teacher-exam-types';
import { ExamFileDropzone } from './ExamFileDropzone';
import { ExamSegmentedControl } from './ExamSegmentedControl';

const CHOICES: AnswerChoice[] = ['-', 'A', 'B', 'C', 'D'];

interface AnswerKeyStepProps {
  draft: ExamWizardDraft;
  onChange: (patch: Partial<ExamWizardDraft>) => void;
}

export function AnswerKeyStep({ draft, onChange }: AnswerKeyStepProps) {
  const questions = draft.questions.length > 0 ? draft.questions : Array.from({ length: 20 }, (_, i) => ({
    id: `q-${i + 1}`,
    number: i + 1,
    preview: '',
    autoDetectedPath: '',
    approvedConceptId: null,
    mappingStatus: 'auto_mapped' as const,
  }));

  const handleUpload = (file: File) => {
    const answers: Record<string, AnswerChoice> = {};
    questions.forEach((q, i) => {
      answers[q.id] = ['A', 'B', 'C', 'D'][i % 4] as AnswerChoice;
    });
    onChange({
      answerKeyUploaded: true,
      answerKeyFileName: file.name,
      answers,
    });
  };

  const setAnswer = (questionId: string, choice: AnswerChoice) => {
    onChange({
      answers: { ...draft.answers, [questionId]: choice },
      answerKeyUploaded: true,
    });
  };

  const manualComplete = questions.every(
    (q) => draft.answers[q.id] && draft.answers[q.id] !== '-',
  );

  return (
    <div className="teacher-exam-step">
      <h2 className="teacher-exam-step__title">Answer key</h2>
      <p className="teacher-exam-step__subtitle">
        Upload or enter the correct answers for all questions.
      </p>

      <ExamSegmentedControl
        options={[
          { value: 'upload', label: 'Upload file' },
          { value: 'manual', label: 'Enter manually' },
        ]}
        value={draft.answerKeyMode}
        onChange={(mode) =>
          onChange({
            answerKeyMode: mode as 'upload' | 'manual',
            answerKeyUploaded: mode === 'upload' ? draft.answerKeyUploaded : false,
          })
        }
      />

      {draft.answerKeyMode === 'upload' ? (
        !draft.answerKeyUploaded ? (
          <ExamFileDropzone
            accept=".txt,.csv,.png,.jpg,.jpeg"
            hint="Drop answer key file here"
            subhint="TXT, CSV, or image · Max 10 MB"
            onFileSelect={handleUpload}
          />
        ) : (
          <div className="teacher-exam-upload-success">
            <div className="teacher-exam-upload-success__header">
              <CheckCircle2 className="h-5 w-5 teacher-exam-upload-success__icon" />
              <div>
                <p className="teacher-exam-upload-success__title">
                  {draft.answerKeyFileName ?? 'Answer key uploaded'}
                </p>
                <p className="teacher-exam-upload-success__meta">
                  {questions.length} answers detected
                </p>
              </div>
              <button
                type="button"
                className="teacher-exam-upload-success__replace"
                onClick={() =>
                  onChange({
                    answerKeyUploaded: false,
                    answerKeyFileName: undefined,
                    answers: {},
                  })
                }
              >
                Replace file
              </button>
            </div>
          </div>
        )
      ) : (
        <div className="teacher-exam-answer-grid">
          {questions.map((q) => (
            <div key={q.id} className="teacher-exam-answer-grid__item">
              <label className="teacher-exam-answer-grid__label">Q{q.number}</label>
              <select
                className="teacher-exam-answer-grid__select"
                value={draft.answers[q.id] ?? '-'}
                onChange={(e) => setAnswer(q.id, e.target.value as AnswerChoice)}
              >
                {CHOICES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function isAnswerKeyValid(draft: ExamWizardDraft): boolean {
  if (draft.answerKeyMode === 'upload') return draft.answerKeyUploaded;
  const count = draft.questions.length > 0 ? draft.questions.length : 20;
  const ids =
    draft.questions.length > 0
      ? draft.questions.map((q) => q.id)
      : Array.from({ length: count }, (_, i) => `q-${i + 1}`);
  return ids.every((id) => draft.answers[id] && draft.answers[id] !== '-');
}
