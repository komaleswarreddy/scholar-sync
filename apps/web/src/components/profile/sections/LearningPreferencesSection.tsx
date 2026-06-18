'use client';

import { PROFILE_LEARNING_PREFS } from '@/lib/profile-mock-data';
import { ProfileField } from '../ProfileField';
import { ProfileFormFooter } from '../ProfileFormFooter';
import { ProfileSummaryHeader } from '../ProfileSummaryHeader';

export function LearningPreferencesSection() {
  const d = PROFILE_LEARNING_PREFS;

  return (
    <div className="profile-main-card">
      <ProfileSummaryHeader />

      <h3 className="text-[16px] font-bold text-[var(--color-home-text)] mt-8 mb-4">
        AI & Study Preferences
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <ProfileField label="AI teaching style" value={d.teachingStyle} type="select" colSpan={2} />
        <ProfileField label="Language" value={d.language} type="select" />
        <ProfileField label="Difficulty" value={d.difficulty} type="select" />
        <ProfileField label="Session length" value={d.sessionLength} type="select" />
      </div>

      <ProfileFormFooter />
    </div>
  );
}
