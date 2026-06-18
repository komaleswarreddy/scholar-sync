'use client';

import Link from 'next/link';
import { ChevronRight } from 'lucide-react';
import { ExamMetaChips } from './ExamMetaChips';
import { ExamStepper } from './ExamStepper';
import type { ExamBoard, ExamWizardStep } from '@/lib/teacher-exam-types';

interface ExamWizardShellProps {
  step: ExamWizardStep;
  examName: string;
  subject: string;
  classNum: number | null;
  section: string;
  examDate: string;
  board: ExamBoard;
  onBack?: () => void;
  backLabel?: string;
  primaryLabel: string;
  onPrimary: () => void;
  primaryDisabled?: boolean;
  children: React.ReactNode;
  hideFooter?: boolean;
  hidePrimary?: boolean;
}

export function ExamWizardShell({
  step,
  examName,
  subject,
  classNum,
  section,
  examDate,
  board,
  onBack,
  backLabel = 'Back',
  primaryLabel,
  onPrimary,
  primaryDisabled = false,
  children,
  hideFooter = false,
  hidePrimary = false,
}: ExamWizardShellProps) {
  return (
    <div className="teacher-exam-page teacher-exam-wizard">
      <nav className="teacher-exam-breadcrumb" aria-label="Breadcrumb">
        <Link href="/teacher/exams" className="teacher-exam-breadcrumb__link">
          Exams
        </Link>
        <ChevronRight className="h-4 w-4 teacher-exam-breadcrumb__sep" />
        <span className="teacher-exam-breadcrumb__current">New exam</span>
      </nav>

      {step <= 5 && <ExamStepper currentStep={step} />}

      {(examName || subject) && step > 1 && step <= 5 && (
        <ExamMetaChips
          examName={examName}
          subject={subject}
          classNum={classNum}
          section={section}
          examDate={examDate}
          board={board}
        />
      )}

      <div className="teacher-exam-wizard-card">{children}</div>

      {!hideFooter && (
        <footer className="teacher-exam-wizard-footer">
          {onBack ? (
            <button type="button" className="teacher-exam-wizard-footer__back" onClick={onBack}>
              {backLabel}
            </button>
          ) : (
            <span />
          )}
          {!hidePrimary && (
            <button
              type="button"
              className="teacher-exam-wizard-footer__primary"
              onClick={onPrimary}
              disabled={primaryDisabled}
            >
              {primaryLabel}
            </button>
          )}
        </footer>
      )}
    </div>
  );
}
