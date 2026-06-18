'use client';

import { ExternalLink, Shield } from 'lucide-react';
import { PROFILE_STUDENT_INFO } from '@/lib/profile-mock-data';
import { ProfileField } from '../ProfileField';
import { ProfileFormFooter } from '../ProfileFormFooter';
import { ProfileSummaryHeader } from '../ProfileSummaryHeader';

export function StudentInfoSection() {
  const d = PROFILE_STUDENT_INFO;

  return (
    <div className="profile-main-card">
      <ProfileSummaryHeader />

      <h3 className="text-[16px] font-bold text-[var(--color-home-text)] mt-8 mb-4">
        Personal Details
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <ProfileField label="Full name" value={d.fullName} />
        <ProfileField label="Date of birth" value={d.dateOfBirth} />
        <ProfileField label="Gender" value={d.gender} type="select" />
        <ProfileField label="Email address" value={d.email} colSpan={2} />
        <ProfileField
          label="Phone number"
          value={d.phone}
          prefix={
            <span className="flex items-center gap-1 text-[13px] font-medium text-[var(--color-home-text-muted)]">
              <span aria-hidden>🇮🇳</span> +91
            </span>
          }
        />
        <ProfileField label="Parent / Guardian contact" value={d.parentContact} colSpan={2} />
        <ProfileField label="City" value={d.city} type="select" />
        <ProfileField label="State" value={d.state} type="select" />
      </div>

      <div className="profile-callout mt-6">
        <Shield className="w-5 h-5 text-[var(--color-brand-text)] flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <p className="text-[14px] font-bold text-[var(--color-brand-primary)]">
            Why we need this information?
          </p>
          <p className="text-[13px] text-[var(--color-home-text-muted)] mt-1 leading-relaxed">
            This helps us personalize your study experience, send important updates, and keep
            your account secure.
          </p>
          <a
            href="#"
            className="inline-flex items-center gap-1 mt-2 text-[13px] font-semibold text-[var(--color-brand-text)] hover:underline"
          >
            Learn more
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>

      <ProfileFormFooter />
    </div>
  );
}
