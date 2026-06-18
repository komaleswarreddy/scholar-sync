'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@clerk/nextjs';
import { TutorModeLanding } from '@/components/tutor/TutorModeLanding';
import { track } from '@/lib/telemetry';

export default function TutorPage() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useUser();

  useEffect(() => {
    track('tutor.viewed');
  }, []);

  if (!isLoaded) {
    return (
      <div className="min-h-screen home-page flex items-center justify-center">
        <p className="text-[var(--color-home-text-muted)]">Loading...</p>
      </div>
    );
  }

  if (!isSignedIn) {
    router.push('/sign-in');
    return (
      <div className="min-h-screen home-page flex items-center justify-center">
        <p className="text-[var(--color-home-text-muted)]">Redirecting...</p>
      </div>
    );
  }

  return <TutorModeLanding />;
}
