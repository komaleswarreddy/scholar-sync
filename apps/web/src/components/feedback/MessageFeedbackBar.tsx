'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ThumbsUp,
  ThumbsDown,
  HelpCircle,
  MinusCircle,
  XCircle,
  BookX,
  Award,
  StickyNote,
  ChevronDown,
  Check,
  Loader2,
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { useUserContext } from '@/contexts/UserContext';
import { useAppToast } from '@/contexts/AppToastContext';

export type FeedbackSignal =
  | 'helpful'
  | 'not_helpful'
  | 'confusing'
  | 'incomplete'
  | 'inaccurate'
  | 'off_syllabus'
  | 'expert_validated'
  | 'missing_dimension'
  | 'expert_note';

type FeedbackRow = {
  id: string;
  signal_type: FeedbackSignal;
  dimension_tag?: string | null;
};

const TIER1: FeedbackSignal[] = ['helpful', 'not_helpful', 'confusing', 'incomplete'];

const DIMENSIONS = [
  { id: 'definition', label: 'Definition' },
  { id: 'intuition', label: 'Intuition' },
  { id: 'misconceptions', label: 'Misconceptions' },
  { id: 'applications', label: 'Applications' },
  { id: 'cross_concept', label: 'Cross-concept' },
  { id: 'mathematical', label: 'Mathematical' },
  { id: 'historical', label: 'Historical' },
  { id: 'exam_traps', label: 'Exam traps' },
  { id: 'visual', label: 'Visual' },
  { id: 'problem_solving', label: 'Problem solving' },
] as const;

function dimensionLabel(id: string | null | undefined): string {
  if (!id) return '';
  return DIMENSIONS.find((d) => d.id === id)?.label ?? id.replace(/_/g, ' ');
}

type MessageFeedbackBarProps = {
  messageId: string;
  compact?: boolean;
};

export function MessageFeedbackBar({ messageId, compact = false }: MessageFeedbackBarProps) {
  const { user } = useUserContext();
  const { showToast } = useAppToast();
  const tier = user?.expertise_tier ?? 'student';
  const [rows, setRows] = useState<FeedbackRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [pendingSignal, setPendingSignal] = useState<FeedbackSignal | null>(null);
  const [moreOpen, setMoreOpen] = useState(false);
  const [expertOpen, setExpertOpen] = useState(false);
  const [textModal, setTextModal] = useState<{
    signal: FeedbackSignal;
    title: string;
    subtitle?: string;
    required?: boolean;
  } | null>(null);
  const [textValue, setTextValue] = useState('');
  /** Default No — chips only appear after user opts in. */
  const [missingAngleOptIn, setMissingAngleOptIn] = useState(false);
  const [selectedDimension, setSelectedDimension] = useState<string | null>(null);
  const [inlineSuccess, setInlineSuccess] = useState<string | null>(null);
  const moreRef = useRef<HTMLDivElement>(null);
  const expertRef = useRef<HTMLDivElement>(null);
  const successTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const canTier2 = ['teacher', 'tutor', 'sme'].includes(tier);
  const canTier3 = ['tutor', 'sme'].includes(tier);

  const signals = rows.map((r) => r.signal_type);
  const tier1Active = TIER1.find((s) => signals.includes(s));
  const missingAngleTags = rows
    .filter((r) => r.signal_type === 'missing_dimension' && r.dimension_tag)
    .map((r) => r.dimension_tag as string);
  const latestMissingTag = missingAngleTags[missingAngleTags.length - 1] ?? null;

  const refresh = useCallback(async () => {
    try {
      const data = await apiClient.listMessageFeedback(messageId);
      setRows(
        data.map((r) => ({
          id: r.id,
          signal_type: r.signal_type as FeedbackSignal,
          dimension_tag: r.dimension_tag,
        })),
      );
    } catch {
      setRows([]);
    }
  }, [messageId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!moreOpen && !expertOpen) return;
    const onPointerDown = (event: MouseEvent) => {
      const target = event.target as Node;
      if (moreOpen && moreRef.current && !moreRef.current.contains(target)) {
        setMoreOpen(false);
      }
      if (expertOpen && expertRef.current && !expertRef.current.contains(target)) {
        setExpertOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMoreOpen(false);
        setExpertOpen(false);
      }
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [moreOpen, expertOpen]);

  useEffect(() => {
    return () => {
      if (successTimerRef.current) clearTimeout(successTimerRef.current);
    };
  }, []);

  const flashSuccess = (message: string) => {
    setInlineSuccess(message);
    if (successTimerRef.current) clearTimeout(successTimerRef.current);
    successTimerRef.current = setTimeout(() => setInlineSuccess(null), 2500);
    void showToast(message);
  };

  const submit = async (
    signal: FeedbackSignal,
    opts?: { free_text?: string; dimension_tag?: string },
  ) => {
    setLoading(true);
    setPendingSignal(signal);
    try {
      await apiClient.submitMessageFeedback(messageId, {
        signal_type: signal,
        free_text: opts?.free_text,
        dimension_tag: opts?.dimension_tag,
      });
      await refresh();

      if (signal === 'missing_dimension' && opts?.dimension_tag) {
        flashSuccess(`Recorded: ${dimensionLabel(opts.dimension_tag)} missing`);
        setMissingAngleOptIn(true);
        setSelectedDimension(opts.dimension_tag);
      } else if (signal === 'expert_validated') {
        flashSuccess('Marked expert-validated');
      } else if (signal === 'expert_note') {
        flashSuccess('Expert note saved');
      } else if (signal === 'inaccurate') {
        flashSuccess('Marked inaccurate');
      } else if (signal === 'off_syllabus') {
        flashSuccess('Marked off syllabus');
      } else {
        flashSuccess('Feedback saved');
      }
    } catch {
      void showToast('Could not save feedback');
    } finally {
      setLoading(false);
      setPendingSignal(null);
      setTextModal(null);
      setTextValue('');
    }
  };

  const pillBase =
    'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed';
  const pillIdle =
    'border-border-default/80 bg-white text-[var(--color-home-text-muted)] hover:bg-black/[0.03] hover:text-[var(--color-home-text)]';
  const pillActive =
    'border-[var(--color-brand-primary)]/30 bg-[var(--color-brand-primary)]/10 text-[var(--color-brand-text)]';

  const primaryPill = (
    signal: FeedbackSignal,
    Icon: typeof ThumbsUp,
    label: string,
    active: boolean,
  ) => (
    <button
      key={signal}
      type="button"
      disabled={loading}
      aria-pressed={active}
      aria-label={label}
      onClick={() => {
        if (signal === 'not_helpful') {
          setTextModal({
            signal,
            title: 'What went wrong?',
            subtitle: 'Optional — helps us improve this answer.',
            required: false,
          });
          return;
        }
        void submit(signal);
      }}
      className={`${pillBase} ${active ? pillActive : pillIdle} ${compact ? 'px-2 py-0.5' : ''}`}
    >
      {pendingSignal === signal ? (
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
      ) : (
        <Icon className="w-3.5 h-3.5 shrink-0" strokeWidth={1.75} />
      )}
      <span>{label}</span>
    </button>
  );

  const menuItem = (
    signal: FeedbackSignal,
    Icon: typeof Award,
    label: string,
    description: string,
    active: boolean,
    onClick: () => void,
  ) => (
    <button
      key={signal}
      type="button"
      disabled={loading}
      onClick={onClick}
      className={`w-full flex items-start gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors ${
        active ? 'bg-purple-50 text-purple-900' : 'hover:bg-black/[0.04] text-text-primary'
      }`}
    >
      <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${active ? 'text-purple-700' : 'text-text-secondary'}`} />
      <span className="min-w-0">
        <span className="block text-xs font-semibold">{label}</span>
        <span className="block text-[11px] text-text-secondary leading-snug mt-0.5">{description}</span>
      </span>
      {active && <Check className="w-3.5 h-3.5 text-purple-700 ml-auto mt-0.5 shrink-0" />}
    </button>
  );

  return (
    <div className="mt-2 flex flex-col gap-1.5">
      <div className="flex flex-wrap items-center gap-1.5">
        {primaryPill('helpful', ThumbsUp, 'Helpful', tier1Active === 'helpful')}
        {primaryPill('not_helpful', ThumbsDown, 'Not helpful', tier1Active === 'not_helpful')}
        {primaryPill('confusing', HelpCircle, 'Confusing', tier1Active === 'confusing')}
        {primaryPill('incomplete', MinusCircle, 'Incomplete', tier1Active === 'incomplete')}

        {canTier2 && (
          <div className="relative" ref={moreRef}>
            <button
              type="button"
              disabled={loading}
              aria-expanded={moreOpen}
              onClick={() => {
                setMoreOpen((o) => !o);
                setExpertOpen(false);
              }}
              className={`${pillBase} ${
                moreOpen || signals.includes('inaccurate') || signals.includes('off_syllabus')
                  ? pillActive
                  : pillIdle
              }`}
            >
              More
              <ChevronDown className={`w-3 h-3 transition-transform ${moreOpen ? 'rotate-180' : ''}`} />
            </button>
            {moreOpen && (
              <div
                className="absolute left-0 top-full z-30 mt-1.5 w-[min(100vw-2rem,280px)] rounded-xl border border-border-default bg-white p-1.5 shadow-lg"
                role="menu"
              >
                <p className="px-2.5 pt-1.5 pb-1 text-[10px] font-semibold uppercase tracking-wide text-text-secondary">
                  Additional feedback
                </p>
                {menuItem(
                  'inaccurate',
                  XCircle,
                  'Inaccurate',
                  'Factually wrong — blocks curation',
                  signals.includes('inaccurate'),
                  () => {
                    setMoreOpen(false);
                    setTextModal({
                      signal: 'inaccurate',
                      title: 'What was incorrect?',
                      subtitle: 'Required — this answer will not enter derived knowledge.',
                      required: true,
                    });
                  },
                )}
                {menuItem(
                  'off_syllabus',
                  BookX,
                  'Off syllabus',
                  'Beyond Class 11–12 curriculum scope',
                  signals.includes('off_syllabus'),
                  () => {
                    setMoreOpen(false);
                    void submit('off_syllabus');
                  },
                )}
              </div>
            )}
          </div>
        )}

        {canTier3 && (
          <div className="relative" ref={expertRef}>
            <button
              type="button"
              disabled={loading}
              aria-expanded={expertOpen}
              onClick={() => {
                setExpertOpen((o) => {
                  const next = !o;
                  if (next) {
                    // Reflect already-submitted missing angle (do not reset to No).
                    if (latestMissingTag) {
                      setMissingAngleOptIn(true);
                      setSelectedDimension(latestMissingTag);
                    } else {
                      setMissingAngleOptIn(false);
                      setSelectedDimension(null);
                    }
                  }
                  return next;
                });
                setMoreOpen(false);
              }}
              className={`${pillBase} ${
                expertOpen ||
                signals.includes('expert_validated') ||
                signals.includes('expert_note') ||
                signals.includes('missing_dimension')
                  ? 'border-purple-300 bg-purple-50 text-purple-800'
                  : pillIdle
              }`}
            >
              Expert
              <ChevronDown className={`w-3 h-3 transition-transform ${expertOpen ? 'rotate-180' : ''}`} />
            </button>
            {expertOpen && (
              <div
                className="absolute left-0 top-full z-30 mt-1.5 w-[min(100vw-2rem,320px)] rounded-xl border border-purple-200 bg-white p-2 shadow-lg"
                role="menu"
              >
                <p className="px-2 pt-1 pb-1.5 text-[10px] font-semibold uppercase tracking-wide text-purple-700">
                  Expert review
                </p>
                {menuItem(
                  'expert_validated',
                  Award,
                  'Expert validated',
                  'Correct and well structured — strong curation signal',
                  signals.includes('expert_validated'),
                  () => void submit('expert_validated'),
                )}
                {menuItem(
                  'expert_note',
                  StickyNote,
                  'Expert note',
                  'Add a correction or addition',
                  signals.includes('expert_note'),
                  () => {
                    setTextModal({
                      signal: 'expert_note',
                      title: 'Add your correction or addition',
                      subtitle: 'Required — your note can become curated knowledge.',
                      required: true,
                    });
                  },
                )}

                <div className="mt-1.5 rounded-lg border border-purple-100 bg-purple-50/60 p-2.5">
                  <p className="text-xs font-semibold text-purple-900">Missing angle</p>
                  {latestMissingTag ? (
                    <div className="mt-1.5 space-y-2">
                      <p className="inline-flex items-center gap-1.5 rounded-full border border-purple-300 bg-white px-2.5 py-1 text-[11px] font-semibold text-purple-900">
                        <Check className="w-3 h-3 text-purple-700" />
                        Submitted: {dimensionLabel(latestMissingTag)}
                      </p>
                      <p className="text-[11px] text-purple-800/80 leading-snug">
                        Change the angle below if you need to update it.
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {DIMENSIONS.map((d) => {
                          const selected = (selectedDimension ?? latestMissingTag) === d.id;
                          return (
                            <button
                              key={d.id}
                              type="button"
                              disabled={loading}
                              onClick={() => {
                                setMissingAngleOptIn(true);
                                setSelectedDimension(d.id);
                              }}
                              className={`rounded-full border px-2 py-0.5 text-[11px] font-medium transition-colors ${
                                selected
                                  ? 'border-purple-500 bg-purple-600 text-white'
                                  : 'border-purple-200 bg-white text-purple-900 hover:border-purple-400'
                              }`}
                            >
                              {d.label}
                            </button>
                          );
                        })}
                      </div>
                      {selectedDimension && selectedDimension !== latestMissingTag && (
                        <button
                          type="button"
                          disabled={loading}
                          onClick={() =>
                            void submit('missing_dimension', { dimension_tag: selectedDimension })
                          }
                          className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-purple-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-purple-800 disabled:opacity-50"
                        >
                          {pendingSignal === 'missing_dimension' ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Check className="w-3.5 h-3.5" />
                          )}
                          Update missing angle
                        </button>
                      )}
                    </div>
                  ) : (
                    <>
                      <p className="text-[11px] text-purple-800/80 mt-0.5 mb-2 leading-snug">
                        Was an important angle of the concept missing from this answer?
                      </p>
                      <div className="flex items-center gap-2 mb-2">
                        <button
                          type="button"
                          disabled={loading}
                          onClick={() => {
                            setMissingAngleOptIn(false);
                            setSelectedDimension(null);
                          }}
                          className={`rounded-full border px-3 py-1 text-[11px] font-semibold transition-colors ${
                            !missingAngleOptIn
                              ? 'border-purple-500 bg-purple-600 text-white'
                              : 'border-purple-200 bg-white text-purple-900 hover:border-purple-400'
                          }`}
                        >
                          No
                        </button>
                        <button
                          type="button"
                          disabled={loading}
                          onClick={() => setMissingAngleOptIn(true)}
                          className={`rounded-full border px-3 py-1 text-[11px] font-semibold transition-colors ${
                            missingAngleOptIn
                              ? 'border-purple-500 bg-purple-600 text-white'
                              : 'border-purple-200 bg-white text-purple-900 hover:border-purple-400'
                          }`}
                        >
                          Yes
                        </button>
                      </div>
                      {missingAngleOptIn && (
                        <>
                          <p className="text-[11px] text-purple-800/80 mb-1.5">
                            Which angle was missing? Select one, then submit.
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {DIMENSIONS.map((d) => {
                              const selected = selectedDimension === d.id;
                              return (
                                <button
                                  key={d.id}
                                  type="button"
                                  disabled={loading}
                                  onClick={() => setSelectedDimension(d.id)}
                                  className={`rounded-full border px-2 py-0.5 text-[11px] font-medium transition-colors ${
                                    selected
                                      ? 'border-purple-500 bg-purple-600 text-white'
                                      : 'border-purple-200 bg-white text-purple-900 hover:border-purple-400'
                                  }`}
                                >
                                  {d.label}
                                </button>
                              );
                            })}
                          </div>
                          <button
                            type="button"
                            disabled={loading || !selectedDimension}
                            onClick={() => {
                              if (!selectedDimension) return;
                              void submit('missing_dimension', { dimension_tag: selectedDimension });
                            }}
                            className="mt-2.5 inline-flex items-center justify-center gap-1.5 rounded-lg bg-purple-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-purple-800 disabled:opacity-50"
                          >
                            {pendingSignal === 'missing_dimension' ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              <Check className="w-3.5 h-3.5" />
                            )}
                            Submit missing angle
                          </button>
                        </>
                      )}
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {(latestMissingTag || inlineSuccess) && (
        <div className="flex flex-wrap items-center gap-1.5">
          {latestMissingTag && (
            <span className="inline-flex items-center gap-1 rounded-full border border-purple-200 bg-purple-50 px-2 py-0.5 text-[11px] font-medium text-purple-800">
              Missing: {dimensionLabel(latestMissingTag)}
            </span>
          )}
          {inlineSuccess && (
            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700">
              <Check className="w-3 h-3" />
              {inlineSuccess}
            </span>
          )}
        </div>
      )}

      {textModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-xl shadow-lg max-w-md w-full p-4">
            <h3 className="font-semibold text-sm text-text-primary">{textModal.title}</h3>
            {textModal.subtitle && (
              <p className="text-xs text-text-secondary mt-1">{textModal.subtitle}</p>
            )}
            <textarea
              className="w-full border border-border-default rounded-lg p-2 text-sm min-h-[88px] mt-3"
              value={textValue}
              onChange={(e) => setTextValue(e.target.value)}
              placeholder={textModal.required ? 'Required details…' : 'Optional details…'}
              autoFocus
            />
            <div className="flex justify-end gap-2 mt-3">
              <button
                type="button"
                className="text-sm px-3 py-1.5 text-text-secondary hover:text-text-primary"
                onClick={() => setTextModal(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="text-sm px-3 py-1.5 rounded-lg bg-[var(--color-brand-primary)] text-white disabled:opacity-50"
                disabled={loading || (textModal.required && !textValue.trim())}
                onClick={() =>
                  void submit(textModal.signal, { free_text: textValue.trim() || undefined })
                }
              >
                {loading ? 'Saving…' : 'Submit'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
