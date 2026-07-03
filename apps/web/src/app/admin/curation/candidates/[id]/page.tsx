'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { apiClient } from '@/lib/api-client';

export default function CurationCandidateDetailPage() {
  const params = useParams();
  const id = typeof params.id === 'string' ? params.id : '';
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [notes, setNotes] = useState('');
  const [confidence, setConfidence] = useState(4);

  useEffect(() => {
    if (!id) return;
    void apiClient.getCurationCandidate(id).then(setDetail);
  }, [id]);

  const review = async (decision: 'approved' | 'rejected') => {
    await apiClient.reviewCurationCandidate(id, {
      decision,
      review_notes: notes || undefined,
      confidence_score: decision === 'approved' ? confidence : undefined,
    });
    window.location.href = '/admin/curation/candidates';
  };

  if (!detail) return <div className="p-6">Loading…</div>;

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-4">
      <h1 className="text-2xl font-bold">Candidate review</h1>
      <pre className="text-xs bg-surface p-3 rounded overflow-auto max-h-64">
        {JSON.stringify(detail, null, 2)}
      </pre>
      <textarea
        className="w-full border rounded p-2 text-sm"
        placeholder="Review notes"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
      />
      <label className="text-sm block">
        Confidence (1–5)
        <input
          type="number"
          min={1}
          max={5}
          value={confidence}
          onChange={(e) => setConfidence(Number(e.target.value))}
          className="ml-2 border rounded px-2"
        />
      </label>
      <div className="flex gap-2">
        <button type="button" className="px-4 py-2 rounded bg-green-600 text-white" onClick={() => void review('approved')}>
          Approve
        </button>
        <button type="button" className="px-4 py-2 rounded bg-red-600 text-white" onClick={() => void review('rejected')}>
          Reject
        </button>
      </div>
    </div>
  );
}
