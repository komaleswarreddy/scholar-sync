'use client';

import { PROFILE_NOTIFICATIONS } from '@/lib/profile-mock-data';
import { ProfileField } from '../ProfileField';
import { ProfileFormFooter } from '../ProfileFormFooter';
import { ProfileSummaryHeader } from '../ProfileSummaryHeader';

function ToggleRow({ label, on }: { label: string; on: boolean }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-[var(--color-home-border)] last:border-0">
      <span className="text-[14px] font-medium text-[var(--color-home-text)]">{label}</span>
      <div
        className={`profile-toggle ${on ? 'profile-toggle--on' : ''}`}
        role="switch"
        aria-checked={on}
      >
        <span className="profile-toggle-knob" />
      </div>
    </div>
  );
}

export function NotificationsSection() {
  const d = PROFILE_NOTIFICATIONS;

  return (
    <div className="profile-main-card">
      <ProfileSummaryHeader />

      <h3 className="text-[16px] font-bold text-[var(--color-home-text)] mt-8 mb-2">
        Alerts & Sharing
      </h3>

      <div className="profile-toggle-list mb-6">
        <ToggleRow label="Study reminders" on={d.studyReminders} />
        <ToggleRow label="Test alerts" on={d.testAlerts} />
        <ToggleRow label="Mastery alerts" on={d.masteryAlerts} />
      </div>

      <ProfileField label="Weekly report sharing" value={d.weeklyReportSharing} type="select" colSpan={2} />

      <ProfileFormFooter />
    </div>
  );
}
