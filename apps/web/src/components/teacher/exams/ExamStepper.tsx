'use client';

import { Check } from 'lucide-react';
import type { ExamWizardStep } from '@/lib/teacher-exam-types';
import { WIZARD_STEP_LABELS } from '@/lib/teacher-exam-types';

interface ExamStepperProps {
  currentStep: ExamWizardStep;
}

const STEPS: ExamWizardStep[] = [1, 2, 3, 4, 5];

export function ExamStepper({ currentStep }: ExamStepperProps) {
  return (
    <nav className="teacher-exam-stepper" aria-label="Exam setup progress">
      <ol className="teacher-exam-stepper__list">
        {STEPS.map((step, index) => {
          const isCompleted = currentStep > step;
          const isActive = currentStep === step;
          const isPending = currentStep < step;

          return (
            <li key={step} className="teacher-exam-stepper__item">
              <div className="teacher-exam-stepper__step">
                <div
                  className={`teacher-exam-stepper__circle${
                    isCompleted
                      ? ' teacher-exam-stepper__circle--completed'
                      : isActive
                        ? ' teacher-exam-stepper__circle--active'
                        : ' teacher-exam-stepper__circle--pending'
                  }`}
                  aria-current={isActive ? 'step' : undefined}
                >
                  {isCompleted ? <Check className="h-4 w-4" strokeWidth={3} /> : step}
                </div>
                <span
                  className={`teacher-exam-stepper__label${
                    isActive ? ' teacher-exam-stepper__label--active' : ''
                  }${isPending ? ' teacher-exam-stepper__label--pending' : ''}`}
                >
                  {WIZARD_STEP_LABELS[step]}
                </span>
              </div>
              {index < STEPS.length - 1 && (
                <div
                  className={`teacher-exam-stepper__connector${
                    isCompleted ? ' teacher-exam-stepper__connector--completed' : ''
                  }`}
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
