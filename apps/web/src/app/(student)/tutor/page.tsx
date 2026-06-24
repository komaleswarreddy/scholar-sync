'use client';

import { useEffect } from 'react';
import { track } from '@/lib/telemetry';
import { TutorModeLanding } from '@/components/tutor/TutorModeLanding';

export default function TutorPage() {
  useEffect(() => {
    track('tutor.viewed');
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 md:px-8 pt-8 md:pt-10 pb-10">
      <TutorModeLanding />
    </div>
  );
}
