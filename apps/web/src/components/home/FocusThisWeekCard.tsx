'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Target, Calendar, ArrowRight } from 'lucide-react';
import { FOCUS_SESSION_URL } from '@/lib/home-mock-data';

type FocusConcept = {
  subject: string;
  topic: string;
  decay_label: string;
};

function ProgressBar({
  label,
  value,
  fillColor,
  trackColor,
}: {
  label: string;
  value: number;
  fillColor: string;
  trackColor: string;
}) {
  return (
    <div>
      <div className="flex justify-between text-[11px] mb-1">
        <span className="text-[var(--color-home-text-muted)] leading-tight">{label}</span>
        <span className="font-semibold text-[var(--color-home-text)] flex-shrink-0 ml-1">
          {value}%
        </span>
      </div>
      <div className={`h-[5px] rounded-full overflow-hidden ${trackColor}`}>
        <div
          className={`h-full rounded-full ${fillColor}`}
          style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
      </div>
    </div>
  );
}

export function FocusThisWeekCard({ focus }: { focus?: FocusConcept | null }) {
  const router = useRouter();
  if (!focus) {
    return (
      <aside className="home-card p-4 flex flex-col h-full bg-white w-full min-h-0">
        <p className="home-section-label mb-3">Focus this week</p>
        <p className="text-[13px] text-[var(--color-home-text-muted)] leading-relaxed">
          Study a notebook to see your focus concept here.
        </p>
      </aside>
    );
  }

  return (
    <aside className="home-card p-4 flex flex-col h-full bg-white w-full min-h-0">
      <p className="home-section-label mb-3">Focus this week</p>

      <div className="flex gap-2 mb-2">
        <div className="w-8 h-8 rounded-full bg-[var(--color-severity-critical-bg)] flex items-center justify-center flex-shrink-0">
          <Target className="w-4 h-4 text-[var(--color-severity-critical)]" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1">
            <h3 className="font-bold text-[var(--color-home-text)] text-[13px] leading-tight">
              {focus.topic}
            </h3>
            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-[var(--color-severity-critical-bg)] text-[var(--color-severity-critical)] uppercase">
              Focus
            </span>
          </div>
          <p className="text-[11px] text-[var(--color-home-text-muted)] mt-1 leading-snug">
            {focus.subject} • {focus.decay_label}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-1.5 text-[11px] text-[var(--color-home-text-muted)] mb-3">
        <Calendar className="w-3.5 h-3.5 flex-shrink-0" />
        <span>Based on your most recent notebook activity</span>
      </div>

      <div className="space-y-2 mb-3">
        <ProgressBar
          label="Focus priority"
          value={focus.decay_label.toLowerCase().includes('review') ? 62 : 35}
          fillColor="bg-[var(--color-progress-decay)]"
          trackColor="bg-orange-100"
        />
        <ProgressBar
          label={`Syllabus progress (${focus.subject})`}
          value={48}
          fillColor="bg-[var(--color-progress-syllabus)]"
          trackColor="bg-teal-50"
        />
        <ProgressBar
          label="Weekly goal progress"
          value={72}
          fillColor="bg-[var(--color-progress-goal)]"
          trackColor="bg-[var(--color-brand-surface)]"
        />
      </div>

      <div className="mt-auto">
        <button
          type="button"
          onClick={() => router.push(FOCUS_SESSION_URL)}
          className="home-btn-primary w-full flex items-center justify-center gap-1.5 rounded-full py-2.5 px-3 text-[12px] font-semibold"
        >
          Start focus session
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
        <Link
          href="/study-planner"
          className="mt-2 block text-center text-[11px] text-[var(--color-brand-primary)] hover:underline font-medium"
        >
          View study plan →
        </Link>
      </div>
    </aside>
  );
}
