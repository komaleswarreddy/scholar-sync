'use client';

import { useUserContext } from '@/contexts/UserContext';
import { emptyProfileLabel } from '@/lib/profile-utils';
import { ProfileField } from '../ProfileField';
import { ProfileFormFooter } from '../ProfileFormFooter';
import { ProfileSummaryHeader } from '../ProfileSummaryHeader';

export function InstituteInfoSection() {
  const { user } = useUserContext();

  return (
    <div className="profile-main-card">
      <ProfileSummaryHeader />

      <h3 className="text-[16px] font-bold text-[var(--color-home-text)] mt-8 mb-4">
        Institute Setup
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <ProfileField
          label="School / Coaching"
          value={emptyProfileLabel(user?.institute)}
          colSpan={2}
          readOnly
        />
        <ProfileField
          label="Batch / Class"
          value={emptyProfileLabel(user?.class_level)}
          colSpan={2}
          readOnly
        />
        <ProfileField label="Username" value={emptyProfileLabel(user?.username)} readOnly />
        <ProfileField label="Contact email" value={emptyProfileLabel(user?.email)} readOnly />
      </div>

      <p className="text-[13px] text-[var(--color-home-text-muted)] mt-4">
        Institute details are set by your school admin. Update them in Student Info if needed.
      </p>

      <ProfileFormFooter />
    </div>
  );
}
