'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api-client';

type CandidateItem = {
  id: string;
  status: string;
  candidate_score: number;
  source_type?: string;
  scoring_signals?: Record<string, unknown>;
  query_text?: string | null;
  user_tier?: string | null;
  created_at?: string | null;
};

function signalLabels(signals?: Record<string, unknown>): string {
  if (!signals || typeof signals !== 'object') return '';
  const parts: string[] = [];
  if (signals.expert_validated) parts.push('Expert validated');
  if (signals.expert_note) parts.push('Expert note');
  if (signals.missing_dimension) {
    const tag = signals.missing_dimension;
    parts.push(
      typeof tag === 'string' && tag !== 'true'
        ? `Missing: ${String(tag).replace(/_/g, ' ')}`
        : 'Missing angle',
    );
  }
  if (signals.user_tier) parts.push(String(signals.user_tier).toUpperCase());
  if (signals.chain_depth) parts.push(`Depth ${signals.chain_depth}`);
  return parts.join(' · ');
}

export default function CurationCandidatesPage() {
  const [items, setItems] = useState<CandidateItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const data = await apiClient.listCurationCandidates({ status: 'pending' });
        setItems(data.items ?? []);
      } catch (e: unknown) {
        setError((e as Error)?.message || 'Failed to load candidates');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-1">Curation candidates</h1>
      <p className="text-sm text-text-secondary mb-4">
        Review expert-flagged interactions. Approve to add derived knowledge for all students.
      </p>
      {loading ? (
        <p>Loading…</p>
      ) : error ? (
        <p className="text-red-600">{error}</p>
      ) : items.length === 0 ? (
        <p className="text-text-secondary">
          No pending candidates. Expert validated / expert note / missing angle feedback creates
          candidates immediately; the batch scorer also runs every few minutes.
        </p>
      ) : (
        <ul className="space-y-2">
          {items.map((c) => (
            <li
              key={c.id}
              className="border border-border-default rounded-xl p-4 flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 bg-white"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-text-primary truncate">
                  {c.query_text?.trim() || `(${c.source_type || 'interaction'})`}
                </p>
                <p className="text-xs text-text-secondary mt-1">
                  {signalLabels(c.scoring_signals) || c.user_tier || 'Pending review'}
                </p>
              </div>
              <Link
                href={`/admin/curation/candidates/${c.id}`}
                className="shrink-0 text-sm font-semibold text-accent-blue hover:underline"
              >
                Review
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
