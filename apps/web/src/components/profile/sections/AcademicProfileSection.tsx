'use client';

import { useUserContext } from '@/contexts/UserContext';
import { emptyProfileLabel } from '@/lib/profile-utils';
import { ProfileField } from '../ProfileField';
import { ProfileFormFooter } from '../ProfileFormFooter';
import { ProfileSummaryHeader } from '../ProfileSummaryHeader';

export function AcademicProfileSection() {
  const { user } = useUserContext();

  return (
    <div className="profile-main-card">
      <ProfileSummaryHeader />

      <h3 className="text-[16px] font-bold text-[var(--color-home-text)] mt-8 mb-4">
        Academic Details
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <ProfileField
          label="Class"
          value={emptyProfileLabel(user?.class_level)}
          readOnly
        />
        <ProfileField label="Board" value="Not set" readOnly />
        <ProfileField label="Stream" value="Not set" readOnly />
        <ProfileField label="Academic year" value="Not set" readOnly />
        <ProfileField
          label="Institute"
          value={emptyProfileLabel(user?.institute)}
          colSpan={2}
          readOnly
        />
      </div>

      <p className="text-[13px] text-[var(--color-home-text-muted)] mt-4">
        Class and institute come from your admin-created account. Board, stream, and subjects will
        be available in a future update.
      </p>

      <ProfileFormFooter />
    </div>
  );
}
