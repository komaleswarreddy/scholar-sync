'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { RECOMMENDED_SESSIONS } from '@/lib/analytics-prep-mock-data';

function subjectTone(subject: string): 'green' | 'orange' {
  return subject === 'Chemistry' ? 'orange' : 'green';
}

export function RecommendedSessionsSection() {
  const router = useRouter();

  return (
    <div className="prep-card prep-recommended-sessions h-full flex flex-col">
      <div className="prep-recommended-header">
        <p className="prep-section-eyebrow">RECOMMENDED NEXT SESSIONS</p>
        <p className="prep-recommended-subtitle">
          Prioritized by weakness, decay, and test proximity
        </p>
      </div>

      <ul className="prep-recommended-list flex-1">
        {RECOMMENDED_SESSIONS.map((s) => (
          <li key={s.id} className="prep-recommended-row">
            <div className="prep-recommended-row-main min-w-0 flex-1">
              <p className="prep-recommended-topic">{s.topic}</p>
              <p className="prep-recommended-meta">
                <span className={`prep-recommended-subject prep-recommended-subject--${subjectTone(s.subject)}`}>
                  {s.subject}
                </span>
                <span className="prep-recommended-meta-sep" aria-hidden>
                  ·
                </span>
                <span>{s.staleDays}d stale</span>
                <span className="prep-recommended-meta-sep" aria-hidden>
                  ·
                </span>
                <span>Test in {s.testInDays}d</span>
              </p>
            </div>
            <span className="prep-recommended-score">{s.score}%</span>
            <button
              type="button"
              onClick={() => router.push(s.focusHref)}
              className="prep-recommended-repair"
            >
              Focus ↗
            </button>
          </li>
        ))}
      </ul>

      <Link href="/analytics" className="prep-recommended-view-all">
        View all recommended sessions →
      </Link>
    </div>
  );
}
