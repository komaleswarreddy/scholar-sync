'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { HomeMobileNav } from '@/components/home/HomeMobileNav';
import { ProblemSolverLanding } from '@/components/problem-solver/ProblemSolverLanding';
import { isProblemSolverEnabled } from '@/lib/feature-flags';
import { track } from '@/lib/telemetry';

export default function ProblemSolverPage() {
  const router = useRouter();

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

  return (
    <div className="max-w-7xl mx-auto px-4 md:px-8 pt-8 md:pt-10 pb-10">
      <HomeMobileNav />
      <ProblemSolverLanding />
    </div>
  );
}
