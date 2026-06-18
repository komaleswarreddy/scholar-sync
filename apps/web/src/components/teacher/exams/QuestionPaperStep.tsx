'use client';

import { CheckCircle2 } from 'lucide-react';
import { buildMockQuestions } from '@/lib/teacher-exam-mock-data';
import type { ExamWizardDraft } from '@/lib/teacher-exam-types';
import { ExamFileDropzone } from './ExamFileDropzone';

interface QuestionPaperStepProps {
  draft: ExamWizardDraft;
  onChange: (patch: Partial<ExamWizardDraft>) => void;
}

export function QuestionPaperStep({ draft, onChange }: QuestionPaperStepProps) {
  const handleUpload = (file: File) => {
    const questions = buildMockQuestions();
    onChange({
      questionPaperUploaded: true,
      questionPaperFileName: file.name,
      questions,
    });
  };

  return (
    <div className="teacher-exam-step">
      <h2 className="teacher-exam-step__title">Question paper</h2>
      <p className="teacher-exam-step__subtitle">
        Upload your question paper. We&apos;ll extract questions automatically.
      </p>

      {!draft.questionPaperUploaded ? (
        <ExamFileDropzone
          accept=".pdf,.doc,.docx"
          hint="Drop your question paper here"
          subhint="PDF or DOCX · Max 20 MB"
          onFileSelect={handleUpload}
        />
      ) : (
        <div className="teacher-exam-upload-success">
          <div className="teacher-exam-upload-success__header">
            <CheckCircle2 className="h-5 w-5 teacher-exam-upload-success__icon" />
            <div>
              <p className="teacher-exam-upload-success__title">
                {draft.questionPaperFileName ?? 'Question paper uploaded'}
              </p>
              <p className="teacher-exam-upload-success__meta">
                {draft.questions.length} questions extracted
              </p>
            </div>
            <button
              type="button"
              className="teacher-exam-upload-success__replace"
              onClick={() =>
                onChange({
                  questionPaperUploaded: false,
                  questionPaperFileName: undefined,
                  questions: [],
                })
              }
            >
              Replace file
            </button>
          </div>

          <div className="teacher-exam-question-preview">
            <table className="teacher-exam-question-preview__table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Question preview</th>
                </tr>
              </thead>
              <tbody>
                {draft.questions.slice(0, 5).map((q) => (
                  <tr key={q.id}>
                    <td>{q.number}</td>
                    <td>{q.preview}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {draft.questions.length > 5 && (
              <p className="teacher-exam-question-preview__more">
                + {draft.questions.length - 5} more questions
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
