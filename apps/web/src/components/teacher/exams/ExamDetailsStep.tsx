'use client';

import { EXAM_BOARDS, EXAM_CLASSES, EXAM_SUBJECTS_BY_CLASS } from '@/lib/teacher-exam-mock-data';
import type { ExamBoard, ExamWizardDraft } from '@/lib/teacher-exam-types';
import { ExamSegmentedControl } from './ExamSegmentedControl';

interface ExamDetailsStepProps {
  draft: ExamWizardDraft;
  onChange: (patch: Partial<ExamWizardDraft>) => void;
}

export function ExamDetailsStep({ draft, onChange }: ExamDetailsStepProps) {
  const subjects =
    draft.classNum != null ? EXAM_SUBJECTS_BY_CLASS[draft.classNum] ?? [] : [];

  return (
    <div className="teacher-exam-step">
      <h2 className="teacher-exam-step__title">Exam details</h2>
      <p className="teacher-exam-step__subtitle">
        Set up the basic information for your exam.
      </p>

      <ExamSegmentedControl
        label="Board"
        options={EXAM_BOARDS.map((b) => ({ value: b, label: b === 'Telangana State Board' ? 'Telangana' : b }))}
        value={draft.board}
        onChange={(board) => onChange({ board: board as ExamBoard })}
      />

      <div className="teacher-exam-form-grid">
        <div className="teacher-exam-field teacher-exam-field--relative">
          <label className="teacher-exam-field__label" htmlFor="exam-class">
            Class <span className="teacher-exam-field__required">*</span>
          </label>
          <select
            id="exam-class"
            className="teacher-exam-field__select"
            value={draft.classNum ?? ''}
            onChange={(e) => {
              const classNum = e.target.value ? Number(e.target.value) : null;
              onChange({
                classNum,
                subject: classNum ? EXAM_SUBJECTS_BY_CLASS[classNum]?.[0] ?? '' : '',
              });
            }}
          >
            <option value="">Select class</option>
            {EXAM_CLASSES.map((c) => (
              <option key={c} value={c}>
                Class {c}
              </option>
            ))}
          </select>
        </div>

        <div className="teacher-exam-field teacher-exam-field--relative">
          <label className="teacher-exam-field__label" htmlFor="exam-subject">
            Subject <span className="teacher-exam-field__required">*</span>
          </label>
          <select
            id="exam-subject"
            className="teacher-exam-field__select"
            value={draft.subject}
            onChange={(e) => onChange({ subject: e.target.value })}
            disabled={!draft.classNum}
          >
            <option value="">Select subject</option>
            {subjects.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        <div className="teacher-exam-field">
          <label className="teacher-exam-field__label" htmlFor="exam-section">
            Section
          </label>
          <input
            id="exam-section"
            type="text"
            className="teacher-exam-field__input"
            placeholder="e.g. A"
            value={draft.section}
            onChange={(e) => onChange({ section: e.target.value })}
          />
        </div>

        <div className="teacher-exam-field">
          <label className="teacher-exam-field__label" htmlFor="exam-name">
            Exam name <span className="teacher-exam-field__required">*</span>
          </label>
          <input
            id="exam-name"
            type="text"
            className="teacher-exam-field__input"
            placeholder="e.g. Mid-term Unit Test"
            value={draft.examName}
            onChange={(e) => onChange({ examName: e.target.value })}
          />
        </div>

        <div className="teacher-exam-field">
          <label className="teacher-exam-field__label" htmlFor="exam-date">
            Exam date <span className="teacher-exam-field__required">*</span>
          </label>
          <input
            id="exam-date"
            type="date"
            className="teacher-exam-field__input"
            value={draft.examDate}
            onChange={(e) => onChange({ examDate: e.target.value })}
          />
        </div>
      </div>

      <div className="teacher-exam-marking">
        <h3 className="teacher-exam-marking__title">Marking scheme</h3>
        <div className="teacher-exam-marking__grid">
          <div className="teacher-exam-field">
            <label className="teacher-exam-field__label" htmlFor="marks-correct">
              Marks per correct
            </label>
            <input
              id="marks-correct"
              type="number"
              min={0}
              step={0.25}
              className="teacher-exam-field__input"
              value={draft.marksCorrect}
              onChange={(e) => onChange({ marksCorrect: Number(e.target.value) })}
            />
          </div>
          <div className="teacher-exam-field">
            <label className="teacher-exam-field__label" htmlFor="marks-wrong">
              Negative marks
            </label>
            <input
              id="marks-wrong"
              type="number"
              min={0}
              step={0.25}
              className="teacher-exam-field__input"
              value={draft.marksWrong}
              onChange={(e) => onChange({ marksWrong: Number(e.target.value) })}
            />
          </div>
          <div className="teacher-exam-field">
            <label className="teacher-exam-field__label" htmlFor="marks-unanswered">
              Unanswered
            </label>
            <input
              id="marks-unanswered"
              type="number"
              min={0}
              step={0.25}
              className="teacher-exam-field__input"
              value={draft.marksUnanswered}
              onChange={(e) => onChange({ marksUnanswered: Number(e.target.value) })}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export function isExamDetailsValid(draft: ExamWizardDraft): boolean {
  return Boolean(
    draft.classNum &&
      draft.subject.trim() &&
      draft.examName.trim() &&
      draft.examDate,
  );
}
