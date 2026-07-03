'use client';

import { useCallback, useEffect, useState } from 'react';
import { ExternalLink, Shield, Loader2 } from 'lucide-react';
import { ProfileField } from '../ProfileField';
import { ProfileFormFooter } from '../ProfileFormFooter';
import { ProfileSummaryHeader } from '../ProfileSummaryHeader';
import { apiClient } from '@/lib/api-client';
import { useUserContext } from '@/contexts/UserContext';
import type { PlatformUser } from '@/lib/platform-auth';
import { profileDisplayName } from '@/lib/profile-utils';

function applyProfileToForm(
  profile: PlatformUser,
  setters: {
    setUsername: (v: string) => void;
    setFirstName: (v: string) => void;
    setLastName: (v: string) => void;
    setEmail: (v: string) => void;
    setMobile: (v: string) => void;
    setInstitute: (v: string) => void;
    setClassLevel: (v: string) => void;
  }
) {
  setters.setUsername(profile.username ?? '');
  setters.setFirstName(profile.first_name ?? '');
  setters.setLastName(profile.last_name ?? '');
  setters.setEmail(profile.email ?? '');
  setters.setMobile(profile.mobile ?? '');
  setters.setInstitute(profile.institute ?? '');
  setters.setClassLevel(profile.class_level ?? '');
}

export function StudentInfoSection() {
  const { user, refreshUser } = useUserContext();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const [username, setUsername] = useState(user?.username ?? '');
  const [firstName, setFirstName] = useState(user?.first_name ?? '');
  const [lastName, setLastName] = useState(user?.last_name ?? '');
  const [email, setEmail] = useState(user?.email ?? '');
  const [mobile, setMobile] = useState(user?.mobile ?? '');
  const [institute, setInstitute] = useState(user?.institute ?? '');
  const [classLevel, setClassLevel] = useState(user?.class_level ?? '');

  const formSetters = {
    setUsername,
    setFirstName,
    setLastName,
    setEmail,
    setMobile,
    setInstitute,
    setClassLevel,
  };

  const loadProfile = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const profile = await apiClient.getMyProfile();
      applyProfileToForm(profile, formSetters);
      await refreshUser();
    } catch {
      setError('Could not load profile. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [refreshUser]);

  useEffect(() => {
    if (user) {
      applyProfileToForm(user, formSetters);
    }
  }, [user]);

  useEffect(() => {
    void loadProfile();
  }, [loadProfile]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await apiClient.updateMyProfile({
        first_name: firstName,
        last_name: lastName,
        email,
        mobile,
        institute,
        class_level: classLevel,
      });
      await refreshUser();
      setSaved(true);
    } catch {
      setError('Failed to save profile.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="profile-main-card flex items-center justify-center py-16">
        <Loader2 className="w-8 h-8 animate-spin text-accent-blue" />
      </div>
    );
  }

  const fullName = profileDisplayName({
    id: user?.id ?? '',
    role: user?.role ?? 'student',
    username,
    first_name: firstName,
    last_name: lastName,
  });

  return (
    <div className="profile-main-card">
      <ProfileSummaryHeader />

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}
      {saved && (
        <div className="mt-4 rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
          Profile saved successfully.
        </div>
      )}

      <h3 className="text-[16px] font-bold text-[var(--color-home-text)] mt-8 mb-4">
        Personal Details
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <ProfileField label="Username" value={username} readOnly colSpan={2} />
        <ProfileField label="Full name" value={fullName} readOnly />
        <ProfileField label="First name" value={firstName} onChange={setFirstName} />
        <ProfileField label="Last name" value={lastName} onChange={setLastName} />
        <ProfileField label="Email address" value={email} onChange={setEmail} colSpan={2} />
        <ProfileField
          label="Phone number"
          value={mobile}
          onChange={setMobile}
          prefix={
            <span className="flex items-center gap-1 text-[13px] font-medium text-[var(--color-home-text-muted)]">
              <span aria-hidden>🇮🇳</span> +91
            </span>
          }
        />
        <ProfileField label="Institute" value={institute} onChange={setInstitute} colSpan={2} />
        <ProfileField label="Class" value={classLevel} onChange={setClassLevel} />
      </div>

      <div className="profile-callout mt-6">
        <Shield className="w-5 h-5 text-[var(--color-brand-text)] flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <p className="text-[14px] font-bold text-[var(--color-brand-primary)]">
            Why we need this information?
          </p>
          <p className="text-[13px] text-[var(--color-home-text-muted)] mt-1 leading-relaxed">
            Your school admin pre-fills these details when creating your account. You can update
            contact and institute info here anytime.
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

      <ProfileFormFooter onSave={() => void handleSave()} onCancel={() => void loadProfile()} />
      {saving && (
        <p className="text-sm text-text-secondary mt-2 flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin" /> Saving…
        </p>
      )}
    </div>
  );
}
