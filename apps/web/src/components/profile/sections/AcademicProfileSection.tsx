'use client';

import { PROFILE_ACADEMIC } from '@/lib/profile-mock-data';
import { ProfileField } from '../ProfileField';
import { ProfileFormFooter } from '../ProfileFormFooter';
import { ProfileSummaryHeader } from '../ProfileSummaryHeader';

export function AcademicProfileSection() {
  const d = PROFILE_ACADEMIC;

  return (
    <div className="profile-main-card">
      <ProfileSummaryHeader />

      <h3 className="text-[16px] font-bold text-[var(--color-home-text)] mt-8 mb-4">
        Academic Details
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <ProfileField label="Class" value={d.classLevel} type="select" />
        <ProfileField label="Board" value={d.board} type="select" />
        <ProfileField label="Stream" value={d.stream} type="select" />
        <ProfileField label="Academic year" value={d.academicYear} type="select" />
        <div className="sm:col-span-2 lg:col-span-3">
          <label className="profile-field-label">Subjects</label>
          <div className="flex flex-wrap gap-2 mt-1">
            {d.subjects.map((s) => (
              <span key={s} className="profile-subject-tag">
                {s}
              </span>
            ))}
          </div>
        </div>
      </div>

      <ProfileFormFooter />
    </div>
  );
}
