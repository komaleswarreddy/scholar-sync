'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@clerk/nextjs';
import { ProblemSolverLanding } from '@/components/problem-solver/ProblemSolverLanding';
import { isProblemSolverEnabled } from '@/lib/feature-flags';
import { track } from '@/lib/telemetry';

export default function ProblemSolverPage() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useUser();

  useEffect(() => {
    if (!isProblemSolverEnabled) {
      router.replace('/home');
      return;
    }
    track('problem_solver.viewed');
  }, [router]);

  if (!isProblemSolverEnabled) {
    return null;
  }

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

  return <ProblemSolverLanding />;
}
