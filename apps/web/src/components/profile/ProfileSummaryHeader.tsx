'use client';

import Image from 'next/image';
import { Camera, ClipboardList } from 'lucide-react';
import { useUserContext } from '@/contexts/UserContext';
import {
  computeProfileCompletion,
  profileClassBoardLine,
  profileDisplayName,
  profileInitials,
} from '@/lib/profile-utils';

type ProfileSummaryHeaderProps = {
  showLandscapeBg?: boolean;
  hideAvatar?: boolean;
};

export function ProfileSummaryHeader({
  showLandscapeBg = false,
  hideAvatar = false,
}: ProfileSummaryHeaderProps) {
  const { user } = useUserContext();
  const initials = profileInitials(user);
  const displayName = profileDisplayName(user);
  const classBoard = profileClassBoardLine(user);
  const usernameLine = user?.username ? `@${user.username}` : '';
  const pct = computeProfileCompletion(user);

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
            <div className="w-[72px] h-[72px] rounded-full bg-[var(--color-brand-primary)] text-white text-[22px] font-bold flex items-center justify-center shadow-sm">
              {initials}
            </div>
            <button
              type="button"
              className="absolute bottom-0 right-0 w-7 h-7 rounded-full bg-white border border-[var(--color-home-border)] flex items-center justify-center shadow-sm"
              aria-label="Change photo"
            >
              <Camera className="w-3.5 h-3.5 text-[var(--color-home-text-muted)]" />
            </button>
          </div>
        )}

        <div className="flex-1 min-w-0">
          <h2 className="text-[20px] font-bold text-[var(--color-home-text)] truncate">{displayName}</h2>
          {usernameLine && (
            <p className="text-[13px] font-mono text-[var(--color-home-text-muted)] mt-0.5">{usernameLine}</p>
          )}
          {classBoard && (
            <p className="text-[14px] text-[var(--color-home-text-muted)] mt-0.5">{classBoard}</p>
          )}
        </div>

        <div className="flex items-center gap-3 sm:ml-auto">
          <div className="flex items-center gap-2 text-[13px] text-[var(--color-home-text-muted)]">
            <ClipboardList className="w-4 h-4" />
            <span>Profile {pct}% complete</span>
          </div>
        </div>
      </div>
    </div>
  );
}
