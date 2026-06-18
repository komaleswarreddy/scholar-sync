'use client';

import { useRouter } from 'next/navigation';
import { Clock, Sparkles } from 'lucide-react';
import { DECAY_BY_SUBJECT } from '@/lib/analytics-prep-mock-data';

const STATUS_COLORS = {
  'at-risk': '#F59E0B',
  fading: '#94A3B8',
  fresh: '#22C55E',
} as const;

function statusLabel(status: 'at-risk' | 'fading' | 'fresh', days: number): string {
  const word = status === 'at-risk' ? 'At risk' : status === 'fading' ? 'Fading' : 'Fresh';
  return `${days}d · ${word}`;
}

export function MasteryDecaySection() {
  const router = useRouter();

  return (
    <div className="prep-card prep-decay-section mb-6">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 mb-4">
        <div>
          <p className="prep-section-eyebrow">MASTERY DECAY</p>
          <h2 className="prep-section-title">What you risk forgetting next</h2>
        </div>
        <p className="text-[12px] text-[var(--color-home-text-muted)] flex items-center gap-1">
          <Clock className="w-3.5 h-3.5" />
          spaced-repetition signals
        </p>
      </div>

      <div className="space-y-6">
        {Object.entries(DECAY_BY_SUBJECT).map(([subject, items]) => (
          <div key={subject}>
            <p className="text-[12px] font-bold tracking-wide text-[var(--color-home-text)] mb-2">
              {subject}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {items.slice(0, 5).map((item) => {
                const statusColor = STATUS_COLORS[item.status];
                return (
                  <div key={item.id} className="prep-decay-card">
                    <div className="flex justify-between items-start gap-3 mb-2 min-h-[44px]">
                      <div className="min-w-0 flex-1 flex items-start gap-2">
                        <span
                          className="prep-decay-dot shrink-0 mt-1"
                          style={{ backgroundColor: statusColor }}
                          aria-hidden
                        />
                        <div className="min-w-0">
                          <p className="text-[14px] font-bold text-[var(--color-home-text)] leading-snug break-words">
                            {item.topic}
                          </p>
                          <p className="text-[11px] text-[var(--color-home-text-muted)] mt-0.5">
                            mastery {item.mastery}%
                          </p>
                        </div>
                      </div>
                      <span
                        className="prep-decay-status shrink-0"
                        style={{ color: statusColor }}
                      >
                        {statusLabel(item.status, item.days)}
                      </span>
                    </div>
                    <div className="prep-progress-bar h-1.5 mb-3">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${item.mastery}%`, backgroundColor: statusColor }}
                      />
                    </div>
                    <div className="flex justify-end">
                      <button
                        type="button"
                        onClick={() => router.push(item.focusHref)}
                        className="prep-decay-recall"
                      >
                        <Sparkles className="w-3.5 h-3.5" />
                        Focus
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
