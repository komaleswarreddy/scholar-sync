'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  BookOpen,
  CheckCircle2,
  Loader2,
  Plus,
  Sparkles,
} from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { TOAST_MIN_VISIBLE_MS, useAppToast } from '@/contexts/AppToastContext';
import { notebookKeys } from '@/hooks/useNotebooks';
import { homeSummaryKeys } from '@/hooks/useHomeSummary';
import { useTutorClass } from '@/contexts/TutorClassContext';
import {
  useTutorChapters,
  useTutorConcepts,
  useTutorFeaturedNotebooks,
  useTutorSubjects,
} from '@/hooks/useTutorCatalog';
import { track } from '@/lib/telemetry';
import { getSubjectTheme } from '@/components/tutor/tutor-subject-theme';
import { TutorNotebookPreparingOverlay } from '@/components/tutor/TutorNotebookPreparingOverlay';
import type { TutorPrepareScope } from '@/lib/tutor-notebook-prepare';
import { warmTutorNcertContext } from '@/lib/tutor-notebook-prepare';
import styles from '@/components/tutor/tutor-mode.module.css';

type Step = 1 | 2 | 3 | 4;

const SOCIAL_SCIENCE_SUBJECT_KEYS = new Set([
  'history',
  'geography',
  'civics-polity',
  'economics',
]);

export function TutorModeLanding() {
  const router = useRouter();
  const { showToast } = useAppToast();
  const queryClient = useQueryClient();

  const { classNum } = useTutorClass();
  const [step, setStep] = useState<Step>(1);
  const [subjectKey, setSubjectKey] = useState<string | null>(null);
  const [subjectLabel, setSubjectLabel] = useState<string>('');
  const [subjectSlug, setSubjectSlug] = useState<string>('');
  const [subsubject, setSubsubject] = useState<string | null>(null);
  const [chapterNo, setChapterNo] = useState<number | null>(null);
  const [chapterTitle, setChapterTitle] = useState<string>('');
  const [conceptId, setConceptId] = useState<string>('all');
  const [conceptLabel, setConceptLabel] = useState<string>('All concepts');
  const [prepareScope, setPrepareScope] = useState<TutorPrepareScope | null>(null);
  const [isPreparing, setIsPreparing] = useState(false);

  const { data: subjects = [], isLoading: subjectsLoading } = useTutorSubjects(classNum);
  const { data: chapters = [], isLoading: chaptersLoading } = useTutorChapters(classNum, subjectKey);
  const { data: concepts = [], isLoading: conceptsLoading } = useTutorConcepts(
    classNum,
    subjectKey,
    chapterNo,
  );
  const { data: featured = [] } = useTutorFeaturedNotebooks(classNum, subjectKey, chapterNo);

  useEffect(() => {
    setStep(1);
    setSubjectKey(null);
    setSubjectLabel('');
    setSubjectSlug('');
    setSubsubject(null);
    setChapterNo(null);
    setChapterTitle('');
    setConceptId('all');
    setConceptLabel('All concepts');
  }, [classNum]);

  const prepareScopePayload = useMemo((): TutorPrepareScope | null => {
    if (!subjectKey || chapterNo == null || !chapterTitle) return null;
    const chapterMeta = chapters.find((c) => c.chapter_no === chapterNo);
    const title = `Ch. ${chapterNo} · ${chapterTitle}`;
    return {
      title,
      classNum,
      subjectKey,
      subjectLabel,
      subjectSlug,
      subsubject,
      chapterNo,
      chapterTitle,
      filterChapterName:
        chapterMeta?.filter_chapter_name ?? chapterTitle.trim().toLowerCase(),
      ncertDocumentId: chapterMeta?.ncert_document_id ?? null,
      chunksCount: chapterMeta?.chunks_count,
      conceptId,
      conceptLabel,
    };
  }, [
    chapterNo,
    chapterTitle,
    chapters,
    classNum,
    conceptId,
    conceptLabel,
    subjectKey,
    subjectLabel,
    subjectSlug,
    subsubject,
  ]);

  useEffect(() => {
    if (step >= 3 && prepareScopePayload) {
      warmTutorNcertContext(prepareScopePayload);
    }
  }, [prepareScopePayload, step]);

  const handlePrepareReady = useCallback(
    async ({
      slug,
      partialFailure,
      timedOut,
    }: {
      slug: string;
      partialFailure: boolean;
      timedOut: boolean;
    }) => {
      if (partialFailure || timedOut) {
        await showToast(
          'Some study assets are still generating — retry from Recent Assets if needed.',
          { minVisibleMs: TOAST_MIN_VISIBLE_MS },
        );
      } else {
        await showToast('Notebook ready', { minVisibleMs: TOAST_MIN_VISIBLE_MS });
      }
      setIsPreparing(false);
      setPrepareScope(null);
      await queryClient.invalidateQueries({ queryKey: notebookKeys.lists() });
      await queryClient.invalidateQueries({ queryKey: homeSummaryKeys.all });
      router.push(`/notebook/${slug}`);
    },
    [queryClient, router, showToast],
  );

  const handlePrepareHardFail = useCallback(
    async (message: string) => {
      await showToast(message, { minVisibleMs: TOAST_MIN_VISIBLE_MS });
    },
    [showToast],
  );

  const handlePrepareCancel = useCallback(() => {
    setIsPreparing(false);
    setPrepareScope(null);
  }, []);

  const handleCreateNotebook = () => {
    if (!prepareScopePayload) return;
    track('tutor.create_notebook', {
      class_num: classNum,
      subject: subjectKey,
      chapter_no: chapterNo,
      concept: conceptId,
    });
    setPrepareScope(prepareScopePayload);
    setIsPreparing(true);
  };

  return (
    <>
      {isPreparing && prepareScope ? (
        <TutorNotebookPreparingOverlay
          scope={prepareScope}
          onReady={(payload) => void handlePrepareReady(payload)}
          onHardFail={(message) => void handlePrepareHardFail(message)}
          onCancel={handlePrepareCancel}
        />
      ) : null}
      <div className={styles.tutorRoot}>
        <div className={styles.pageWrap}>
          <div className="mb-8">
            <h1 className="text-2xl md:text-3xl font-semibold text-[var(--color-home-text)]">
              Tutor Mode
            </h1>
            <p className="text-[14px] text-[var(--color-home-text-muted)] mt-2 max-w-xl">
              Pick a subject and chapter, then study with NCERT-grounded answers and citations.
            </p>
          </div>

          <div className={styles.pageBody}>
            {step >= 1 && (
              <section className={styles.section}>
                <StepHeader n={1} title="Choose a subject" active={step === 1} />
                {subjectsLoading ? (
                  <LoadingRow />
                ) : (
                  <div className={styles.subjectGrid}>
                    {subjects.map((subject) => {
                      const theme = getSubjectTheme(subject.id);
                      const { Icon } = theme;
                      const selected = subjectKey === subject.id;
                      return (
                        <button
                          key={subject.id}
                          type="button"
                          onClick={() => {
                            setSubjectKey(subject.id);
                            setSubjectLabel(subject.label);
                            setSubjectSlug(subject.subject_slug);
                            setSubsubject(subject.subsubject ?? null);
                            setChapterNo(null);
                            setConceptId('all');
                            setConceptLabel('All concepts');
                            setStep(2);
                          }}
                          className={`${styles.subjectCard}${selected ? ` ${styles.subjectCardSelected}` : ''}`}
                        >
                          {selected ? (
                            <CheckCircle2 className={styles.subjectCheck} strokeWidth={1.75} aria-hidden />
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
            )}

            {step >= 2 && subjectKey && (
              <section className={styles.section}>
                <StepHeader n={2} title="Choose a chapter" active={step === 2} />
                {chaptersLoading ? (
                  <LoadingRow />
                ) : (
                  <div className={styles.chapterGrid}>
                    {chapters.map((chapter) => {
                      const selected = chapterNo === chapter.chapter_no;
                      const showFeatured =
                        chapter.is_featured_chapter && (chapter.featured_count || 0) > 0;
                      const hasMetaRow = showFeatured || chapter.concept_count > 0;
                      const showChapterHint = !chapter.summary && !hasMetaRow;
                      return (
                        <button
                          key={chapter.chapter_no}
                          type="button"
                          onClick={() => {
                            setChapterNo(chapter.chapter_no);
                            setChapterTitle(chapter.title);
                            setConceptId('all');
                            setConceptLabel('All concepts');
                            setStep(3);
                          }}
                          className={`${styles.chapterCard}${selected ? ` ${styles.chapterCardSelected}` : ''}`}
                        >
                          {selected ? (
                            <CheckCircle2 className={styles.chapterCheck} strokeWidth={1.75} aria-hidden />
                          ) : null}
                          <span className={styles.chapterNumber}>{chapter.chapter_no}</span>
                          <div className={styles.chapterBody}>
                            <p className={styles.chapterTitle}>
                              Chapter {chapter.chapter_no} · {chapter.title}
                            </p>
                            {chapter.summary ? (
                              <p className={styles.chapterDescription}>{chapter.summary}</p>
                            ) : null}
                            {showChapterHint ? (
                              <p className={styles.chapterHint}>Select to study this chapter</p>
                            ) : null}
                            {hasMetaRow ? (
                              <div className={styles.chapterMeta}>
                                {showFeatured ? (
                                  <span className={styles.featuredBadge}>
                                    <Sparkles className="w-3 h-3" strokeWidth={1.75} aria-hidden />
                                    {chapter.featured_count} FEATURED
                                  </span>
                                ) : null}
                                {chapter.concept_count > 0 ? (
                                  <span className={styles.conceptCount}>
                                    {chapter.concept_count} concepts
                                  </span>
                                ) : null}
                              </div>
                            ) : null}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </section>
            )}

            {step >= 3 && chapterNo != null && (
              <section className={styles.section}>
                <StepHeader n={3} title="Narrow to a concept (optional)" active={step === 3} />
                {conceptsLoading ? (
                  <LoadingRow />
                ) : (
                  <div className={styles.conceptRow}>
                    {concepts.map((concept) => {
                      const selected = conceptId === concept.id;
                      return (
                        <button
                          key={concept.id}
                          type="button"
                          onClick={() => {
                            setConceptId(concept.id);
                            setConceptLabel(concept.label);
                            setStep(4);
                          }}
                          className={`${styles.conceptPill}${selected ? ` ${styles.conceptPillSelected}` : ''}`}
                        >
                          {concept.label}
                        </button>
                      );
                    })}
                  </div>
                )}
              </section>
            )}

            {step >= 3 && chapterNo != null && (
              <section className={styles.section}>
                <StepHeader n={4} title="Start studying" active={step >= 4} />
                <div className={styles.startGrid}>
                  <div className={styles.studyCard}>
                    <div className={styles.studyCardHeader}>
                      <div className={`${styles.studyCardIconWrap} ${styles.studyCardIconCustom}`}>
                        <Plus className="w-5 h-5" strokeWidth={1.75} />
                      </div>
                      <div className={styles.studyCardHeaderText}>
                        <p className={styles.studyCardLabel}>Custom</p>
                        <h3 className={styles.studyCardTitle}>Create custom notebook</h3>
                      </div>
                    </div>
                    <p className={styles.studyCardDescription}>
                      Build a notebook scoped to your selected chapter and optional concept. Chat
                      answers will cite NCERT sources from your selection.
                    </p>
                    <div className={styles.summaryPanel}>
                      <SummaryRow label="Subject" value={subjectLabel || '—'} />
                      <SummaryRow
                        label="Chapter"
                        value={chapterNo != null ? `Ch. ${chapterNo} · ${chapterTitle}` : '—'}
                      />
                      <SummaryRow label="Concept" value={conceptLabel} />
                    </div>
                    <button
                      type="button"
                      disabled={!subjectKey || chapterNo == null || isPreparing}
                      onClick={() => handleCreateNotebook()}
                      className={styles.createBtn}
                    >
                      {isPreparing ? (
                        <>
                          <Loader2 className={`w-4 h-4 ${styles.spinner}`} />
                          Preparing…
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-4 h-4" strokeWidth={1.75} />
                          Create notebook
                        </>
                      )}
                    </button>
                  </div>

                  <div className={styles.studyCard}>
                    <div className={styles.studyCardHeader}>
                      <div className={`${styles.studyCardIconWrap} ${styles.studyCardIconCurated}`}>
                        <Sparkles className="w-5 h-5" strokeWidth={1.75} />
                      </div>
                      <div className={styles.studyCardHeaderText}>
                        <p className={styles.studyCardLabel}>Curated</p>
                        <h3 className={styles.studyCardTitle}>Open a featured notebook</h3>
                      </div>
                    </div>
                    <p className={styles.studyCardDescription}>
                      Jump into a pre-built notebook for this chapter, curated by your instructors or
                      team.
                    </p>
                    {featured.length === 0 ? (
                      <div className={styles.emptyState}>
                        <BookOpen className={`w-8 h-8 ${styles.emptyStateIcon}`} strokeWidth={1.75} />
                        <p className={styles.emptyStateTitle}>No featured notebooks yet</p>
                        <p className={styles.emptyStateDescription}>
                          Try creating a custom notebook for this chapter.
                        </p>
                      </div>
                    ) : (
                      <ul className={styles.featuredList}>
                        {featured.map((nb) => (
                          <li key={nb.id}>
                            <button
                              type="button"
                              onClick={() => router.push(`/notebook/${nb.slug}`)}
                              className={styles.featuredItem}
                            >
                              {nb.title}
                            </button>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              </section>
            )}
          </div>
        </div>
      </div>
    </>
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

function StepHeader({ n, title, active }: { n: number; title: string; active: boolean }) {
  return (
    <div className={styles.sectionHeader}>
      <span className={`${styles.stepBadge}${active ? '' : ` ${styles.stepBadgeInactive}`}`}>{n}</span>
      <h2 className={styles.sectionTitle}>{title}</h2>
    </div>
  );
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.summaryRow}>
      <span className={styles.summaryLabel}>{label}</span>
      <span className={styles.summaryValue}>{value}</span>
    </div>
  );
}

function LoadingRow() {
  return (
    <div className={styles.loadingRow}>
      <Loader2 className={`w-4 h-4 ${styles.spinner}`} strokeWidth={1.75} />
      Loading…
    </div>
  );
}
