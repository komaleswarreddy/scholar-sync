'use client';

import { ChevronRight, Eye } from 'lucide-react';
import { useUserContext } from '@/contexts/UserContext';
import { computeProfileCompletion } from '@/lib/profile-utils';

export function ProfileCompletionSidebar() {
  const { user } = useUserContext();
  const pct = computeProfileCompletion(user);
  const r = 22;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (pct / 100) * circumference;

  return (
    <div className="profile-sidebar-completion">
      <div className="flex gap-3">
        <div className="relative w-[52px] h-[52px] flex-shrink-0">
          <svg className="w-[52px] h-[52px] -rotate-90" viewBox="0 0 52 52">
            <circle cx="26" cy="26" r={r} fill="none" stroke="#E8EBE9" strokeWidth="5" />
            <circle
              cx="26"
              cy="26"
              r={r}
              fill="none"
              stroke="var(--color-brand-text)"
              strokeWidth="5"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
            />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center text-[12px] font-bold text-[var(--color-brand-text)]">
            {pct}%
          </span>
        </div>
        <div className="min-w-0">
          <p className="text-[14px] font-bold text-[var(--color-home-text)] leading-snug">
            {pct >= 100 ? 'Profile complete!' : pct >= 70 ? 'Almost there!' : 'Complete your profile'}
          </p>
          <p className="text-[12px] text-[var(--color-home-text-muted)] mt-1 leading-relaxed">
            Fill in details from your admin account or update them in Student Info.
          </p>
        </div>
      </div>
      <button
        type="button"
        className="mt-3 flex items-center gap-1.5 text-[13px] font-semibold text-[var(--color-brand-text)] hover:underline w-full"
      >
        <Eye className="w-4 h-4" strokeWidth={1.75} />
        Preview profile
        <ChevronRight className="w-4 h-4 ml-auto" />
      </button>
    </div>
  );
}
