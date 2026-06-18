'use client';

import { PROFILE_INSTITUTE } from '@/lib/profile-mock-data';
import { ProfileField } from '../ProfileField';
import { ProfileFormFooter } from '../ProfileFormFooter';
import { ProfileSummaryHeader } from '../ProfileSummaryHeader';

export function InstituteInfoSection() {
  const d = PROFILE_INSTITUTE;

  return (
    <div className="profile-main-card">
      <ProfileSummaryHeader />

      <h3 className="text-[16px] font-bold text-[var(--color-home-text)] mt-8 mb-4">
        Institute Setup
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <ProfileField label="School / Coaching" value={d.schoolCoaching} colSpan={2} />
        <ProfileField label="Batch" value={d.batch} colSpan={2} />
        <ProfileField label="Mentor" value={d.mentor} />
        <ProfileField label="Institute code" value={d.instituteCode} />
      </div>

      <ProfileFormFooter />
    </div>
  );
}
