'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Award,
  CheckCircle2,
  Loader2,
  MessageSquareText,
  StickyNote,
  Tag,
  XCircle,
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';

type InteractionLog = {
  id: string;
  query_text?: string | null;
  chain_depth?: number | null;
  user_tier?: string | null;
};

type Feedback = {
  id: string;
  signal_type?: string | null;
  dimension_tag?: string | null;
  free_text?: string | null;
  user_tier?: string | null;
};

type CandidateDetail = {
  id: string;
  status: string;
  candidate_score?: number;
  scoring_signals?: Record<string, unknown> | null;
  source_type?: string | null;
  interaction_log?: InteractionLog | null;
  feedback?: Feedback | null;
  artifact_preview?: string | null;
  created_at?: string | null;
};

const SIGNAL_LABELS: Record<string, string> = {
  expert_validated: 'Expert validated',
  expert_note: 'Expert note',
  missing_dimension: 'Missing angle',
  helpful: 'Helpful',
  inaccurate: 'Inaccurate',
  off_syllabus: 'Off syllabus',
};

function formatSignalType(signal?: string | null): string {
  if (!signal) return 'Feedback';
  return SIGNAL_LABELS[signal] ?? signal.replace(/_/g, ' ');
}

function formatDimension(tag?: string | null): string {
  if (!tag) return '';
  return tag.replace(/_/g, ' ');
}

function formatTier(tier?: string | null): string {
  if (!tier) return '—';
  return tier.toUpperCase();
}

function reasonChips(signals?: Record<string, unknown> | null, feedback?: Feedback | null): string[] {
  const chips: string[] = [];
  if (signals?.expert_validated) chips.push('Expert validated');
  if (signals?.expert_note) chips.push('Expert note');
  if (signals?.missing_dimension) {
    const tag = signals.missing_dimension;
    chips.push(
      typeof tag === 'string' && tag !== 'true'
        ? `Missing: ${formatDimension(tag)}`
        : 'Missing angle',
    );
  }
  if (signals?.user_tier) chips.push(String(signals.user_tier).toUpperCase());
  if (signals?.chain_depth) chips.push(`Chain depth ${signals.chain_depth}`);
  if (signals?.helpful_high_tier) chips.push('Helpful (expert tier)');
  if (signals?.inaccurate) chips.push('Inaccurate (blocked)');
  if (feedback?.signal_type && chips.length === 0) {
    chips.push(formatSignalType(feedback.signal_type));
  }
  if (feedback?.dimension_tag && !chips.some((c) => c.startsWith('Missing:'))) {
    chips.push(`Missing: ${formatDimension(feedback.dimension_tag)}`);
  }
  return chips;
}

function statusStyles(status: string): string {
  switch (status) {
    case 'approved':
      return 'bg-emerald-50 text-emerald-800 border-emerald-200';
    case 'rejected':
      return 'bg-red-50 text-red-800 border-red-200';
    default:
      return 'bg-amber-50 text-amber-900 border-amber-200';
  }
}

export default function CurationCandidateDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = typeof params.id === 'string' ? params.id : '';
  const [detail, setDetail] = useState<CandidateDetail | null>(null);
  const [notes, setNotes] = useState('');
  const [confidence, setConfidence] = useState(4);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState<'approved' | 'rejected' | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    void (async () => {
      try {
        const data = (await apiClient.getCurationCandidate(id)) as CandidateDetail;
        setDetail(data);
      } catch (e: unknown) {
        setError((e as Error)?.message || 'Failed to load candidate');
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  const chips = useMemo(
    () => reasonChips(detail?.scoring_signals, detail?.feedback ?? null),
    [detail],
  );

  const queryText = detail?.interaction_log?.query_text?.trim() || '';

  const metaItems = useMemo(() => {
    if (!detail) return [] as Array<{ label: string; value: string }>;
    const items: Array<{ label: string; value: string }> = [];
    const tierVal = detail.interaction_log?.user_tier || detail.feedback?.user_tier;
    if (tierVal) items.push({ label: 'Contributor tier', value: formatTier(tierVal) });
    if (detail.source_type) {
      items.push({
        label: 'Source',
        value: detail.source_type.replace(/_/g, ' '),
      });
    }
    const depth = detail.interaction_log?.chain_depth;
    if (depth != null && depth > 0) {
      items.push({ label: 'Chain depth', value: String(depth) });
    }
    return items;
  }, [detail]);

  const review = async (decision: 'approved' | 'rejected') => {
    setSubmitting(decision);
    setError(null);
    try {
      await apiClient.reviewCurationCandidate(id, {
        decision,
        review_notes: notes.trim() || undefined,
        confidence_score: decision === 'approved' ? confidence : undefined,
      });
      router.push('/admin/curation/candidates');
    } catch (e: unknown) {
      setError((e as Error)?.message || `Failed to ${decision}`);
      setSubmitting(null);
    }
  };

  if (loading) {
    return (
      <div className="p-6 max-w-3xl mx-auto flex items-center gap-2 text-text-secondary">
        <Loader2 className="w-4 h-4 animate-spin" />
        Loading candidate…
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="p-6 max-w-3xl mx-auto space-y-3">
        <p className="text-red-600">{error || 'Candidate not found'}</p>
        <Link href="/admin/curation/candidates" className="text-sm text-accent-blue hover:underline">
          Back to candidates
        </Link>
      </div>
    );
  }

  const isPending = detail.status === 'pending';
  const showQuestionCard = Boolean(queryText) || metaItems.length > 0;

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link
            href="/admin/curation/candidates"
            className="inline-flex items-center gap-1.5 text-sm text-text-secondary hover:text-text-primary mb-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to candidates
          </Link>
          <h1 className="text-2xl font-semibold text-text-primary">Candidate review</h1>
          <p className="text-sm text-text-secondary mt-1">
            Review this expert-flagged interaction, then approve or reject.
          </p>
        </div>
        <span
          className={`shrink-0 rounded-full border px-2.5 py-1 text-xs font-semibold capitalize ${statusStyles(detail.status)}`}
        >
          {detail.status}
        </span>
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {showQuestionCard && (
        <section
          className={`rounded-2xl border border-border-default bg-white p-5 shadow-sm ${
            queryText && metaItems.length > 0 ? 'space-y-4' : ''
          }`}
        >
          {queryText && (
            <div className="flex items-start gap-3">
              <div className="mt-0.5 rounded-lg bg-accent-blue/10 p-2 text-accent-blue">
                <MessageSquareText className="w-4 h-4" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold uppercase tracking-wide text-text-secondary">
                  Student / expert question
                </p>
                <p className="mt-1 text-[15px] font-medium text-text-primary leading-relaxed">
                  {queryText}
                </p>
              </div>
            </div>
          )}

          {metaItems.length > 0 && (
            <div
              className={`grid gap-3 ${
                metaItems.length === 1
                  ? 'grid-cols-1'
                  : metaItems.length === 2
                    ? 'grid-cols-2'
                    : 'grid-cols-2 sm:grid-cols-3'
              } ${queryText ? 'pt-1' : ''}`}
            >
              {metaItems.map((item) => (
                <div
                  key={item.label}
                  className="rounded-xl border border-border-default/70 bg-[#f8fafb] px-3 py-2.5"
                >
                  <p className="text-[11px] font-medium text-text-secondary">{item.label}</p>
                  <p className="text-sm font-semibold text-text-primary mt-0.5 capitalize">
                    {item.value}
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {chips.length > 0 && (
        <section className="rounded-2xl border border-border-default bg-white p-5 shadow-sm space-y-3">
          <div className="flex items-center gap-2">
            <Award className="w-4 h-4 text-purple-700" />
            <h2 className="text-sm font-semibold text-text-primary">Why it was flagged</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            {chips.map((chip) => (
              <span
                key={chip}
                className="inline-flex items-center gap-1 rounded-full border border-purple-200 bg-purple-50 px-2.5 py-1 text-xs font-medium text-purple-900"
              >
                <Tag className="w-3 h-3" />
                {chip}
              </span>
            ))}
          </div>
        </section>
      )}

      {detail.feedback && (detail.feedback.free_text || detail.feedback.signal_type) && (
        <section className="rounded-2xl border border-border-default bg-white p-5 shadow-sm space-y-3">
          <div className="flex items-center gap-2">
            <StickyNote className="w-4 h-4 text-text-secondary" />
            <h2 className="text-sm font-semibold text-text-primary">Expert feedback</h2>
          </div>
          <div className="rounded-xl border border-border-default/70 bg-[#f8fafb] px-4 py-3">
            <p className="text-xs font-semibold text-text-secondary">
              {formatSignalType(detail.feedback.signal_type)}
              {detail.feedback.dimension_tag
                ? ` · ${formatDimension(detail.feedback.dimension_tag)}`
                : ''}
            </p>
            {detail.feedback.free_text ? (
              <p className="mt-2 text-sm text-text-primary leading-relaxed whitespace-pre-wrap">
                “{detail.feedback.free_text}”
              </p>
            ) : null}
          </div>
        </section>
      )}

      {detail.artifact_preview ? (
        <section className="rounded-2xl border border-border-default bg-white p-5 shadow-sm space-y-2">
          <h2 className="text-sm font-semibold text-text-primary">Artifact preview</h2>
          <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
            {detail.artifact_preview}
          </p>
        </section>
      ) : null}

      {isPending ? (
        <section className="rounded-2xl border border-border-default bg-white p-5 shadow-sm space-y-4">
          <h2 className="text-sm font-semibold text-text-primary">Your review</h2>
          <div>
            <label htmlFor="review-notes" className="block text-xs font-medium text-text-secondary mb-1.5">
              Review notes (optional)
            </label>
            <textarea
              id="review-notes"
              className="w-full min-h-[96px] rounded-xl border border-border-default px-3 py-2.5 text-sm text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-2 focus:ring-accent-blue/30"
              placeholder="Add context for why you approve or reject…"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="confidence" className="block text-xs font-medium text-text-secondary mb-1.5">
              Confidence if approving (1–5)
            </label>
            <div className="flex items-center gap-2">
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setConfidence(n)}
                  className={`h-9 w-9 rounded-lg border text-sm font-semibold transition-colors ${
                    confidence === n
                      ? 'border-accent-blue bg-accent-blue/10 text-accent-blue'
                      : 'border-border-default bg-white text-text-secondary hover:bg-surface-hover'
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
          <div className="flex flex-col sm:flex-row gap-2 pt-1">
            <button
              type="button"
              disabled={!!submitting}
              onClick={() => void review('approved')}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              {submitting === 'approved' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <CheckCircle2 className="w-4 h-4" />
              )}
              Approve
            </button>
            <button
              type="button"
              disabled={!!submitting}
              onClick={() => void review('rejected')}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm font-semibold text-red-700 hover:bg-red-100 disabled:opacity-50"
            >
              {submitting === 'rejected' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <XCircle className="w-4 h-4" />
              )}
              Reject
            </button>
          </div>
        </section>
      ) : (
        <section className="rounded-2xl border border-border-default bg-white p-5 shadow-sm">
          <p className="text-sm text-text-secondary">
            This candidate is already <span className="font-semibold capitalize">{detail.status}</span>.
          </p>
        </section>
      )}
    </div>
  );
}
