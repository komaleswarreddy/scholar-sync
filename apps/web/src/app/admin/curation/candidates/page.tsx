'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { apiClient } from '@/lib/api-client';

export default function CurationCandidatesPage() {
  const [items, setItems] = useState<Array<{ id: string; status: string; candidate_score: number }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void (async () => {
      try {
        const data = await apiClient.listCurationCandidates({ status: 'pending' });
        setItems(data.items ?? []);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Curation candidates</h1>
      {loading ? (
        <p>Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-text-secondary">No pending candidates.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((c) => (
            <li key={c.id} className="border rounded-lg p-3 flex justify-between items-center">
              <span>Score {c.candidate_score}</span>
              <Link href={`/admin/curation/candidates/${c.id}`} className="text-accent-blue text-sm font-medium">
                Review
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
