'use client';

import { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useUserContext } from '@/contexts/UserContext';
import { ProfileShell, ProfileSectionContent } from '@/components/profile';
import {
  DEFAULT_PROFILE_SECTION,
  isValidProfileSection,
  type ProfileSectionId,
} from '@/lib/profile-sections';

export default function ProfileSectionPage() {
  const params = useParams();
  const router = useRouter();
  const { loading, isSignedIn, refreshUser } = useUserContext();

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
    if (!loading && !isSignedIn) {
      router.replace('/sign-in');
      return;
    }
    if (isSignedIn) {
      void refreshUser();
    }
  }, [loading, isSignedIn, router, refreshUser]);

  return (
    <ProfileShell sectionId={sectionId}>
      <ProfileSectionContent sectionId={sectionId} />
    </ProfileShell>
  );
}
