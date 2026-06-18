'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@clerk/nextjs';
import {
  CustomPlanModal,
  GlobalStudyPlanCalendarModal,
  StartNewPlanSection,
  StudyPlanPageHeader,
  StudyPlanPageShell,
  YourPlansSection,
} from '@/components/study-planner';
import { useStudyPlans } from '@/lib/study-planner-storage';

export default function StudyPlannerPage() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useUser();
  const { plans, hydrated, addPlan } = useStudyPlans();
  const [modalOpen, setModalOpen] = useState(false);
  const [calendarOpen, setCalendarOpen] = useState(false);

  useEffect(() => {
    if (isLoaded && !isSignedIn) router.push('/sign-in');
  }, [isLoaded, isSignedIn, router]);

  if (!isLoaded || !isSignedIn || !hydrated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <p className="text-text-secondary">Loading...</p>
      </div>
    );
  }

  return (
    <StudyPlanPageShell>
      <StudyPlanPageHeader onOpenCalendar={() => setCalendarOpen(true)} />

      <div id="your-plans">
        <YourPlansSection plans={plans} />
      </div>

      <StartNewPlanSection
        onPlanCreated={addPlan}
        onOpenCustomModal={() => setModalOpen(true)}
      />

      <CustomPlanModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onPlanCreated={addPlan}
      />

      <GlobalStudyPlanCalendarModal
        isOpen={calendarOpen}
        onClose={() => setCalendarOpen(false)}
        plans={plans}
      />
    </StudyPlanPageShell>
  );
}
