'use client';

import { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { Calendar, Sparkles, X } from 'lucide-react';
import { useTutorClass } from '@/contexts/TutorClassContext';
import { useTutorChapters } from '@/hooks/useTutorCatalog';
import {
  CHAPTER_FALLBACK,
  mergeChapterOptions,
  STUDY_PLAN_SUBJECTS,
} from '@/lib/study-planner-mock-data';
import {
  createCustomPlan,
  getDefaultFormState,
  validateCustomPlanForm,
} from '@/lib/study-planner-storage';
import type {
  CustomPlanFormState,
  DurationUnit,
  StudyPlan,
  StudyPlanSubjectId,
  StudyTimeMode,
  TimelineMode,
} from '@/lib/study-planner-types';
import { useAppToast } from '@/contexts/AppToastContext';
import { ChapterAccordion } from './ChapterAccordion';
import { SegmentedControl } from './SegmentedControl';
import { SelectableChip } from './SelectableChip';

type CustomPlanModalProps = {
  isOpen: boolean;
  onClose: () => void;
  onPlanCreated: (plan: StudyPlan) => void;
};

function SubjectChaptersLoader({
  subjectId,
  classNum,
  form,
  expanded,
  onToggleExpand,
  onToggleChapter,
}: {
  subjectId: StudyPlanSubjectId;
  classNum: number;
  form: CustomPlanFormState;
  expanded: boolean;
  onToggleExpand: () => void;
  onToggleChapter: (chapterNo: number) => void;
}) {
  const subject = STUDY_PLAN_SUBJECTS.find((s) => s.id === subjectId)!;
  const { data: apiChapters } = useTutorChapters(classNum, subject.apiKey);
  const chapters = useMemo(() => {
    if (subjectId !== 'mathematics') {
      return CHAPTER_FALLBACK[subjectId];
    }
    return mergeChapterOptions(subjectId, apiChapters);
  }, [subjectId, apiChapters]);
  const selected = form.selectedChapters[subjectId] ?? [];

  return (
    <ChapterAccordion
      subjectLabel={subject.label}
      chapters={chapters}
      selectedChapterNos={selected}
      expanded={expanded}
      onToggleExpand={onToggleExpand}
      onToggleChapter={onToggleChapter}
    />
  );
}

export function CustomPlanModal({ isOpen, onClose, onPlanCreated }: CustomPlanModalProps) {
  const { classNum } = useTutorClass();
  const { showToast } = useAppToast();
  const [mounted, setMounted] = useState(false);
  const [form, setForm] = useState<CustomPlanFormState>(getDefaultFormState());
  const [expandedSubjects, setExpandedSubjects] = useState<Record<string, boolean>>({});

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (isOpen) {
      setForm(getDefaultFormState());
      setExpandedSubjects({});
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isOpen, onClose]);

  const validation = validateCustomPlanForm(form);

  const toggleSubject = (id: StudyPlanSubjectId) => {
    setForm((prev) => {
      const isSelected = prev.selectedSubjects.includes(id);
      if (isSelected) {
        const nextSubjects = prev.selectedSubjects.filter((s) => s !== id);
        const nextChapters = { ...prev.selectedChapters };
        delete nextChapters[id];
        return { ...prev, selectedSubjects: nextSubjects, selectedChapters: nextChapters };
      }
      setExpandedSubjects((e) => ({ ...e, [id]: true }));
      return { ...prev, selectedSubjects: [...prev.selectedSubjects, id] };
    });
  };

  const toggleChapter = (subjectId: StudyPlanSubjectId, chapterNo: number) => {
    setForm((prev) => {
      const current = prev.selectedChapters[subjectId] ?? [];
      const next = current.includes(chapterNo)
        ? current.filter((n) => n !== chapterNo)
        : [...current, chapterNo];
      return {
        ...prev,
        selectedChapters: { ...prev.selectedChapters, [subjectId]: next },
      };
    });
  };

  const handleGenerate = () => {
    if (!validation.valid) return;
    const plan = createCustomPlan(form);
    onPlanCreated(plan);
    showToast('Custom study plan created');
    onClose();
    document.getElementById('your-plans')?.scrollIntoView({ behavior: 'smooth' });
  };

  if (!isOpen || !mounted) return null;

  return createPortal(
    <div
      className="assets-modal-backdrop study-plan-page"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="presentation"
    >
      <div
        className="study-plan-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="custom-plan-title"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="study-plan-modal-header">
          <h2 id="custom-plan-title" className="study-plan-modal-title">
            Create your custom plan
          </h2>
          <p className="study-plan-modal-subtitle">
            We&apos;ll generate a study schedule based on what you tell us.
          </p>
          <button
            type="button"
            className="study-plan-modal-close"
            onClick={onClose}
            aria-label="Close"
          >
            <X className="w-5 h-5" strokeWidth={1.75} />
          </button>
        </header>

        <div className="study-plan-modal-body">
          <div>
            <p className="study-plan-modal-section-label">Subjects</p>
            <div className="flex flex-wrap gap-2">
              {STUDY_PLAN_SUBJECTS.map((subject) => (
                <SelectableChip
                  key={subject.id}
                  label={subject.label}
                  selected={form.selectedSubjects.includes(subject.id)}
                  onClick={() => toggleSubject(subject.id)}
                  variant="subject"
                />
              ))}
            </div>
          </div>

          {form.selectedSubjects.length > 0 && (
            <div>
              <p className="study-plan-modal-section-label">Chapters</p>
              <div className="flex flex-col gap-3">
                {form.selectedSubjects.map((subjectId) => (
                  <SubjectChaptersLoader
                    key={subjectId}
                    subjectId={subjectId}
                    classNum={classNum}
                    form={form}
                    expanded={expandedSubjects[subjectId] ?? true}
                    onToggleExpand={() =>
                      setExpandedSubjects((e) => ({
                        ...e,
                        [subjectId]: !(e[subjectId] ?? true),
                      }))
                    }
                    onToggleChapter={(chapterNo) => toggleChapter(subjectId, chapterNo)}
                  />
                ))}
              </div>
            </div>
          )}

          <div>
            <p className="study-plan-modal-section-label">Timeline</p>
            <SegmentedControl
              ariaLabel="Timeline mode"
              options={[
                { value: 'end_date', label: 'By end date' },
                { value: 'duration', label: 'By duration' },
              ]}
              value={form.timelineMode}
              onChange={(v) => setForm((prev) => ({ ...prev, timelineMode: v as TimelineMode }))}
            />
            {form.timelineMode === 'end_date' ? (
              <div className="study-plan-date-wrap">
                <input
                  type="date"
                  className="study-plan-input study-plan-input--wide"
                  value={form.endDate}
                  onChange={(e) => setForm((prev) => ({ ...prev, endDate: e.target.value }))}
                />
                <Calendar className="study-plan-date-icon w-4 h-4" strokeWidth={1.75} />
              </div>
            ) : (
              <div className="flex gap-3 mt-3">
                <input
                  type="number"
                  min={1}
                  className="study-plan-input"
                  value={form.durationValue}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      durationValue: Math.max(1, Number(e.target.value) || 1),
                    }))
                  }
                />
                <select
                  className="study-plan-select"
                  value={form.durationUnit}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      durationUnit: e.target.value as DurationUnit,
                    }))
                  }
                >
                  <option value="Days">Days</option>
                  <option value="Weeks">Weeks</option>
                  <option value="Months">Months</option>
                </select>
              </div>
            )}
          </div>

          <div>
            <p className="study-plan-modal-section-label">Time you can study</p>
            <SegmentedControl
              ariaLabel="Study time mode"
              options={[
                { value: 'per_day', label: 'Per day' },
                { value: 'per_week', label: 'Per week' },
              ]}
              value={form.studyTimeMode}
              onChange={(v) =>
                setForm((prev) => ({ ...prev, studyTimeMode: v as StudyTimeMode }))
              }
            />
            {form.studyTimeMode === 'per_day' ? (
              <div className="study-plan-input-row">
                <span className="study-plan-input-label">Hours per day</span>
                <input
                  type="number"
                  min={0.5}
                  step={0.5}
                  className="study-plan-input"
                  value={form.hoursPerDay}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      hoursPerDay: Math.max(0.5, Number(e.target.value) || 0.5),
                    }))
                  }
                />
              </div>
            ) : (
              <div className="study-plan-input-row">
                <span className="study-plan-input-label">Days per week</span>
                <input
                  type="number"
                  min={1}
                  max={7}
                  className="study-plan-input"
                  value={form.daysPerWeek}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      daysPerWeek: Math.min(7, Math.max(1, Number(e.target.value) || 1)),
                    }))
                  }
                />
              </div>
            )}
          </div>
        </div>

        <footer className="study-plan-modal-footer">
          <p className="study-plan-modal-hint">{validation.message}</p>
          <div className="study-plan-modal-actions">
            <button type="button" className="study-plan-modal-cancel" onClick={onClose}>
              Cancel
            </button>
            <button
              type="button"
              className="study-plan-modal-generate"
              disabled={!validation.valid}
              onClick={handleGenerate}
            >
              <Sparkles className="w-4 h-4" strokeWidth={1.75} />
              Generate plan
            </button>
          </div>
        </footer>
      </div>
    </div>,
    document.body,
  );
}
