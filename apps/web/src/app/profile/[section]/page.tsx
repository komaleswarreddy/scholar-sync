'use client';

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useUser } from '@clerk/nextjs';
import { ProfileShell, ProfileSectionContent } from '@/components/profile';
import {
  DEFAULT_PROFILE_SECTION,
  isValidProfileSection,
  type ProfileSectionId,
} from '@/lib/profile-sections';

export default function ProfileSectionPage() {
  const params = useParams();
  const router = useRouter();
  const { isLoaded, isSignedIn } = useUser();

  const raw = typeof params.section === 'string' ? params.section : '';
  const sectionId: ProfileSectionId = isValidProfileSection(raw)
    ? raw
    : DEFAULT_PROFILE_SECTION;

  useEffect(() => {
    if (!isValidProfileSection(raw) && raw) {
      router.replace(`/profile/${DEFAULT_PROFILE_SECTION}`);
    }
  }, [raw, router]);

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.replace('/sign-in');
    }
  }, [isLoaded, isSignedIn, router]);

  if (!isLoaded) {
    return (
      <div className="min-h-screen home-page flex items-center justify-center">
        <p className="text-[var(--color-home-text-muted)]">Loading...</p>
      </div>
    );
  }

  return (
    <ProfileShell sectionId={sectionId}>
      <ProfileSectionContent sectionId={sectionId} />
    </ProfileShell>
  );
}
