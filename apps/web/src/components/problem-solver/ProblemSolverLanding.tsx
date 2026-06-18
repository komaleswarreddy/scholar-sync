'use client';

import { useCallback, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { BookOpenText, CheckCircle2, ChevronRight, Loader2, Sparkles } from 'lucide-react';
import { HomeTopNav } from '@/components/home/HomeTopNav';
import { useTutorClass } from '@/contexts/TutorClassContext';
import { useTutorSubjects } from '@/hooks/useTutorCatalog';
import { useCreateNotebook } from '@/hooks/useNotebooks';
import { getSubjectTheme } from '@/components/tutor/tutor-subject-theme';
import styles from '@/components/tutor/tutor-mode.module.css';

const SOCIAL_SCIENCE_SUBJECT_KEYS = new Set([
  'history',
  'geography',
  'civics-polity',
  'economics',
]);

export function ProblemSolverLanding() {
  const router = useRouter();
  const { classNum, setClassNum } = useTutorClass();
  const createNotebook = useCreateNotebook();
  const { data: subjects = [], isLoading: subjectsLoading } = useTutorSubjects(classNum);
  const [entryMode, setEntryMode] = useState<'entry' | 'subject'>('entry');
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
  const [isCreating, setIsCreating] = useState(false);

  const selectedSubjects = useMemo(
    () => subjects.filter((s) => selectedKeys.has(s.id)),
    [subjects, selectedKeys],
  );

  const toggleSubject = useCallback((subjectId: string) => {
    setSelectedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(subjectId)) {
        next.delete(subjectId);
      } else {
        next.add(subjectId);
      }
      return next;
    });
  }, []);

  const handleOpenNotebook = async () => {
    if (selectedSubjects.length === 0 || isCreating) return;
    setIsCreating(true);
    try {
      const notebook = await createNotebook.mutateAsync({
        title: 'Problem Solver',
        mode: 'problem_solver',
        class_level: String(classNum),
        settings: {
          problem_solver_scope: {
            class_num: classNum,
            subject_keys: selectedSubjects.map((s) => s.id),
            subject_labels: selectedSubjects.map((s) => s.label),
          },
        },
      });
      router.push(`/notebook/${notebook.slug}`);
    } finally {
      setIsCreating(false);
    }
  };

  const handleOpenCustomNotebook = async () => {
    if (isCreating) return;
    setIsCreating(true);
    try {
      const notebook = await createNotebook.mutateAsync({
        title: 'Custom Notebook',
        mode: 'problem_solver',
        class_level: '12',
        settings: {
          problem_solver_scope: {
            class_num: 12,
            subject_keys: [],
            subject_labels: [],
          },
        },
      });
      router.push(`/notebook/${notebook.slug}`);
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="min-h-screen home-page flex flex-col">
      <HomeTopNav activeStyle="pill" />
      <div className={styles.tutorRoot}>
        <div className={styles.pageWrap}>
          <div className="mb-8">
            <h1 className="text-2xl md:text-3xl font-semibold text-[var(--color-home-text)]">
              Problem Solver
            </h1>
            <p className="text-[14px] text-[var(--color-home-text-muted)] mt-2 max-w-xl">
              Choose one or more subjects, then upload a problem for guided, NCERT-grounded solving.
            </p>
          </div>

          <div className={styles.pageBody}>
            {entryMode === 'entry' ? (
              <section className={styles.section}>
                <div className={styles.sectionHeader}>
                  <span className={styles.stepBadge}>1</span>
                  <h2 className={styles.sectionTitle}>Choose your workspace</h2>
                </div>
                <div className={styles.startGrid}>
                  <button
                    type="button"
                    className={styles.studyCard}
                    onClick={() => {
                      setClassNum(12);
                      setEntryMode('subject');
                    }}
                  >
                    <div className={styles.studyCardHeader}>
                      <div className={`${styles.studyCardIconWrap} ${styles.studyCardIconCurated}`}>
                        <BookOpenText className="w-5 h-5" />
                      </div>
                      <div className={styles.studyCardHeaderText}>
                        <p className={styles.studyCardLabel}>Class 12</p>
                        <p className={styles.studyCardTitle}>Subject Notebook</p>
                      </div>
                    </div>
                    <p className={styles.studyCardDescription}>
                      Pick your Class 12 subject first, then open a problem solver notebook scoped to those subjects.
                    </p>
                  </button>
                  <button
                    type="button"
                    className={styles.studyCard}
                    onClick={() => void handleOpenCustomNotebook()}
                    disabled={isCreating}
                  >
                    <div className={styles.studyCardHeader}>
                      <div className={`${styles.studyCardIconWrap} ${styles.studyCardIconCustom}`}>
                        <Sparkles className="w-5 h-5" />
                      </div>
                      <div className={styles.studyCardHeaderText}>
                        <p className={styles.studyCardLabel}>Open Directly</p>
                        <p className={styles.studyCardTitle}>Custom Notebook</p>
                      </div>
                    </div>
                    <p className={styles.studyCardDescription}>
                      Jump directly into a fresh notebook and ask any question without selecting subjects.
                    </p>
                  </button>
                </div>
              </section>
            ) : (
              <>
                <section className={styles.section}>
                  <div className={styles.sectionHeader}>
                    <span className={styles.stepBadge}>1</span>
                    <h2 className={styles.sectionTitle}>Choose subject(s)</h2>
                  </div>
                  {subjectsLoading ? (
                    <div className={styles.loadingRow}>
                      <Loader2 className={`w-4 h-4 ${styles.spinner}`} strokeWidth={1.75} />
                      Loading…
                    </div>
                  ) : (
                    <div className={styles.subjectGrid}>
                      {subjects.map((subject) => {
                        const theme = getSubjectTheme(subject.id);
                        const { Icon } = theme;
                        const selected = selectedKeys.has(subject.id);
                        return (
                          <button
                            key={subject.id}
                            type="button"
                            onClick={() => toggleSubject(subject.id)}
                            className={`${styles.subjectCard}${selected ? ` ${styles.subjectCardSelected}` : ''}`}
                            aria-pressed={selected}
                          >
                            {selected ? (
                              <CheckCircle2
                                className={styles.subjectCheck}
                                strokeWidth={1.75}
                                aria-hidden
                              />
                            ) : null}
                            <div
                              className={styles.subjectIconWrap}
                              style={{ backgroundColor: theme.iconBg, color: theme.iconColor }}
                            >
                              <Icon className="w-5 h-5" strokeWidth={1.75} />
                            </div>
                            <div className={styles.subjectTextBlock}>
                              <p className={styles.subjectLabel}>{subjectPrimaryName(subject)}</p>
                              {SOCIAL_SCIENCE_SUBJECT_KEYS.has(subject.id) ? (
                                <p className={styles.subjectCategory}>Social Science</p>
                              ) : null}
                              <p className={styles.subjectMeta}>
                                {subject.chapter_count} chapters available
                              </p>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </section>

                <section className={styles.section}>
                  <button
                    type="button"
                    className={styles.psSecondaryBtn}
                    onClick={() => {
                      setEntryMode('entry');
                      setSelectedKeys(new Set());
                    }}
                  >
                    Back
                  </button>
                </section>

                {selectedSubjects.length > 0 ? (
                  <section className={styles.section}>
                    <div className={styles.summaryPanel}>
                      <SummaryRow
                        label="Class"
                        value={`Class ${classNum}`}
                      />
                      <SummaryRow
                        label="Subjects"
                        value={selectedSubjects.map((s) => subjectPrimaryName(s)).join(', ')}
                      />
                    </div>
                    <button
                      type="button"
                      disabled={isCreating}
                      onClick={() => void handleOpenNotebook()}
                      className={styles.createBtn}
                    >
                      {isCreating ? (
                        <>
                          <Loader2 className={`w-4 h-4 ${styles.spinner}`} />
                          Opening notebook…
                        </>
                      ) : (
                        <>
                          Open notebook
                          <ChevronRight className="w-4 h-4" strokeWidth={1.75} />
                        </>
                      )}
                    </button>
                  </section>
                ) : null}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function subjectPrimaryName(subject: {
  id: string;
  label: string;
  subsubject?: string | null;
}): string {
  if (subject.subsubject?.trim()) {
    return subject.subsubject.trim();
  }
  if (SOCIAL_SCIENCE_SUBJECT_KEYS.has(subject.id)) {
    return subject.label.split(' · ')[0]?.trim() || subject.label;
  }
  return subject.label;
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.summaryRow}>
      <span className={styles.summaryLabel}>{label}</span>
      <span className={styles.summaryValue}>{value}</span>
    </div>
  );
}
