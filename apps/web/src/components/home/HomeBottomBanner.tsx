'use client';

import { useRouter } from 'next/navigation';
import { Trophy } from 'lucide-react';

export function HomeBottomBanner() {
  const router = useRouter();

  return (
    <div className="rounded-2xl bg-[var(--color-brand-muted)] border border-[rgba(13,61,46,0.08)] px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div className="flex items-start sm:items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center flex-shrink-0 shadow-sm">
          <Trophy className="w-5 h-5 text-[var(--color-brand-primary)]" />
        </div>
        <p className="text-[14px] text-[var(--color-brand-primary)] font-medium leading-relaxed">
          Keep it up! You&apos;re consistent this week. 2 more focused sessions to hit your goal.
        </p>
      </div>
      <button
        type="button"
        onClick={() => router.push('/dashboard')}
        className="flex-shrink-0 rounded-full bg-white border border-[var(--color-brand-primary)] text-[var(--color-brand-primary)] px-6 py-2.5 text-[14px] font-semibold hover:bg-[var(--color-brand-surface)] transition-colors self-start sm:self-center"
      >
        Study now
      </button>
    </div>
  );
}
