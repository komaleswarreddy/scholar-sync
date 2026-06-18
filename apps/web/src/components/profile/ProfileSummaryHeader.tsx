'use client';

import Image from 'next/image';
import { Camera, ClipboardList } from 'lucide-react';
import { useUser } from '@clerk/nextjs';
import {
  PROFILE_COMPLETION_PERCENT,
  PROFILE_DISPLAY,
} from '@/lib/profile-mock-data';

type ProfileSummaryHeaderProps = {
  showLandscapeBg?: boolean;
  /** Hide avatar (Exam Goals — white header aligned with other profile sections) */
  hideAvatar?: boolean;
};

export function ProfileSummaryHeader({
  showLandscapeBg = false,
  hideAvatar = false,
}: ProfileSummaryHeaderProps) {
  const { user } = useUser();
  const initials =
    user?.firstName?.[0] && user?.lastName?.[0]
      ? `${user.firstName[0]}${user.lastName[0]}`
      : PROFILE_DISPLAY.initials;
  const displayName = user?.fullName || PROFILE_DISPLAY.fullName;
  const pct = PROFILE_COMPLETION_PERCENT;

  return (
    <div
      className={`profile-summary-header relative overflow-hidden ${showLandscapeBg ? 'profile-summary-header--landscape' : ''}`}
    >
      {showLandscapeBg && (
        <div className="profile-summary-landscape" aria-hidden>
          <Image
            src="/images/home/hero-landscape-right.png"
            alt=""
            width={400}
            height={200}
            className="profile-summary-landscape-img"
          />
        </div>
      )}

      <div className="relative z-[1] flex flex-col sm:flex-row sm:items-center gap-4 sm:gap-6 min-h-[88px]">
        {!hideAvatar && (
          <div className="relative flex-shrink-0">
            {user?.imageUrl ? (
              <img
                src={user.imageUrl}
                alt=""
                className="w-[72px] h-[72px] rounded-full object-cover border-2 border-white shadow-sm"
              />
            ) : (
              <div className="w-[72px] h-[72px] rounded-full bg-[var(--color-brand-primary)] text-white text-[22px] font-bold flex items-center justify-center shadow-sm">
                {initials}
              </div>
            )}
            <button
              type="button"
              className="absolute -bottom-0.5 -right-0.5 w-7 h-7 rounded-full bg-white border border-[var(--color-home-border)] flex items-center justify-center shadow-sm text-[var(--color-home-text-muted)] hover:text-[var(--color-brand-text)]"
              aria-label="Change photo"
            >
              <Camera className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        <div className="flex-1 min-w-0">
          <h2 className="text-[20px] font-bold text-[var(--color-home-text)]">{displayName}</h2>
          <p className="text-[14px] text-[var(--color-home-text-muted)] mt-0.5">
            {PROFILE_DISPLAY.classBoard}
          </p>
          <p className="text-[14px] text-[var(--color-home-text-muted)]">{PROFILE_DISPLAY.track}</p>
        </div>

        <div className="profile-completion-widget flex-shrink-0 sm:ml-auto">
          <div className="flex items-center gap-2 mb-1">
            <ClipboardList className="w-4 h-4 text-[var(--color-brand-text)]" strokeWidth={1.75} />
            <span className="text-[12px] font-medium text-[var(--color-home-text-muted)]">
              Profile completion
            </span>
          </div>
          <p className="text-[28px] font-bold text-[var(--color-brand-text)] leading-none">{pct}%</p>
          <div className="profile-completion-bar mt-2">
            <div className="profile-completion-bar-fill" style={{ width: `${pct}%` }} />
          </div>
          <p className="text-[11px] text-[var(--color-home-text-muted)] mt-1.5">
            Keep it up! You&apos;re doing great.
          </p>
        </div>
      </div>
    </div>
  );
}
