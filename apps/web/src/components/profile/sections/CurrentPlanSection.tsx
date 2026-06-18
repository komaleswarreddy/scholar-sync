'use client';

import { PROFILE_CURRENT_PLAN } from '@/lib/profile-mock-data';
import { ProfileField } from '../ProfileField';
import { ProfileFormFooter } from '../ProfileFormFooter';
import { ProfileSummaryHeader } from '../ProfileSummaryHeader';

export function CurrentPlanSection() {
  const d = PROFILE_CURRENT_PLAN;

  return (
    <div className="profile-main-card">
      <ProfileSummaryHeader />

      <h3 className="text-[16px] font-bold text-[var(--color-home-text)] mt-8 mb-4">
        Subscription & Access
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <ProfileField label="Product plan" value={d.planName} />
        <ProfileField label="Renewal" value={d.renewal} />
        <ProfileField label="Limits" value={d.limits} colSpan={2} />
        <ProfileField label="Access" value={d.access} colSpan={2} />
      </div>

      <ProfileFormFooter />
    </div>
  );
}
