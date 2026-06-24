'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { AnswerKeyStep, isAnswerKeyValid } from '@/components/teacher/exams/AnswerKeyStep';
import { ConceptMappingStep } from '@/components/teacher/exams/ConceptMappingStep';
import { ExamDetailsStep, isExamDetailsValid } from '@/components/teacher/exams/ExamDetailsStep';
import { ExamGradedSuccess } from '@/components/teacher/exams/ExamGradedSuccess';
import { ExamWizardShell } from '@/components/teacher/exams/ExamWizardShell';
import { OmrSheetsStep } from '@/components/teacher/exams/OmrSheetsStep';
import { QuestionPaperStep } from '@/components/teacher/exams/QuestionPaperStep';
import { CONCEPT_CATALOG, createEmptyDraft } from '@/lib/teacher-exam-mock-data';
import {
  finishExamAsGraded,
  getDraft,
  getExamById,
  loadDraftFromExam,
  saveDraft,
} from '@/lib/teacher-exam-storage';
import { TeacherWizardSkeleton } from '@/components/skeleton';
import type { ExamWizardDraft, ExamWizardStep } from '@/lib/teacher-exam-types';

export default function NewExamPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const examIdParam = searchParams.get('examId');
  const viewGraded = searchParams.get('view') === 'graded';

  const [draft, setDraft] = useState<ExamWizardDraft>(createEmptyDraft);
  const [hydrated, setHydrated] = useState(false);
  const [gradedSummary, setGradedSummary] = useState<ReturnType<typeof finishExamAsGraded> | null>(null);

  useEffect(() => {
    if (examIdParam) {
      const fromExam = loadDraftFromExam(examIdParam);
      if (fromExam) {
        if (viewGraded) {
          const exam = getExamById(examIdParam);
          if (exam?.gradingSummary) {
            setGradedSummary(exam);
            setDraft({ ...fromExam, step: 6 });
            setHydrated(true);
            return;
          }
        }
        setDraft(fromExam);
      }
    } else {
      const saved = getDraft();
      if (saved.examId || saved.examName) {
        setDraft(saved);
      }
    }
    setHydrated(true);
  }, [examIdParam, viewGraded]);

  const updateDraft = useCallback((patch: Partial<ExamWizardDraft>) => {
    setDraft((prev) => {
      const next = { ...prev, ...patch };
      if (!next.examId && next.examName.trim()) {
        next.examId = prev.examId ?? `exam-${Date.now()}`;
      }
      saveDraft(next);
      return next;
    });
  }, []);

  const goToStep = (step: ExamWizardStep) => {
    updateDraft({ step });
  };

  const handleBack = () => {
    if (draft.step > 1) goToStep((draft.step - 1) as ExamWizardStep);
    else router.push('/teacher/exams');
  };

  const handleFinish = () => {
    const graded = finishExamAsGraded(draft);
    setGradedSummary(graded);
    goToStep(6);
  };

  const primaryConfig = useMemo(() => {
    switch (draft.step) {
      case 1:
        return {
          label: 'Continue to question paper',
          disabled: !isExamDetailsValid(draft),
          action: () => goToStep(2),
        };
      case 2:
        return {
          label: 'Continue to concept mapping',
          disabled: !draft.questionPaperUploaded,
          action: () => goToStep(3),
        };
      case 3:
        return {
          label: 'Approve all and continue',
          disabled: false,
          action: () => {
            const approved = draft.questions.map((q) => {
              if (q.approvedConceptId) {
                return { ...q, mappingStatus: 'auto_mapped' as const };
              }
              const fallback = CONCEPT_CATALOG.find((c) => c.path === q.autoDetectedPath);
              return {
                ...q,
                approvedConceptId: fallback?.id ?? q.approvedConceptId,
                mappingStatus: 'auto_mapped' as const,
              };
            });
            updateDraft({ questions: approved, step: 4 });
          },
        };
      case 4:
        return {
          label: draft.answerKeyMode === 'upload' ? 'Upload key' : 'Save key and continue',
          disabled: !isAnswerKeyValid(draft),
          action: () => goToStep(5),
        };
      case 5:
        return { label: '', disabled: true, action: () => {} };
      default:
        return { label: '', disabled: true, action: () => {} };
    }
  }, [draft]);

  if (!hydrated) {
    return <TeacherWizardSkeleton />;
  }

  if (draft.step === 6 && gradedSummary?.gradingSummary) {
    return (
      <div className="teacher-exam-page teacher-exam-wizard">
        <ExamGradedSuccess
          examId={gradedSummary.id}
          examName={gradedSummary.examName}
          summary={gradedSummary.gradingSummary}
        />
      </div>
    );
  }

  return (
    <ExamWizardShell
      step={draft.step}
      examName={draft.examName}
      subject={draft.subject}
      classNum={draft.classNum}
      section={draft.section}
      examDate={draft.examDate}
      board={draft.board}
      onBack={handleBack}
      primaryLabel={draft.step === 5 ? 'Finish and grade' : primaryConfig.label}
      onPrimary={draft.step === 5 ? () => {} : primaryConfig.action}
      primaryDisabled={draft.step === 5 ? true : primaryConfig.disabled}
      hidePrimary={draft.step === 5}
    >
      {draft.step === 1 && <ExamDetailsStep draft={draft} onChange={updateDraft} />}
      {draft.step === 2 && <QuestionPaperStep draft={draft} onChange={updateDraft} />}
      {draft.step === 3 && <ConceptMappingStep draft={draft} onChange={updateDraft} />}
      {draft.step === 4 && <AnswerKeyStep draft={draft} onChange={updateDraft} />}
      {draft.step === 5 && (
        <OmrSheetsStep draft={draft} onChange={updateDraft} onFinish={handleFinish} />
      )}
    </ExamWizardShell>
  );
}
