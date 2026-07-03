'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUserContext } from '@/contexts/UserContext';
import {
  CustomPlanModal,
  GlobalStudyPlanCalendarModal,
  StartNewPlanSection,
  StudyPlanPageHeader,
  StudyPlanPageShell,
  YourPlansSection,
} from '@/components/study-planner';
import { HomeOverviewSkeleton } from '@/components/skeleton';
import { useStudyPlans } from '@/lib/study-planner-storage';

export default function StudyPlannerPage() {
  const router = useRouter();
  const { loading, isSignedIn } = useUserContext();
  const { plans, hydrated, addPlan } = useStudyPlans();
  const [modalOpen, setModalOpen] = useState(false);
  const [calendarOpen, setCalendarOpen] = useState(false);

  useEffect(() => {
    if (!loading && !isSignedIn) router.push('/sign-in');
  }, [loading, isSignedIn, router]);

  return (
    <StudyPlanPageShell>
      <StudyPlanPageHeader onOpenCalendar={() => setCalendarOpen(true)} />

      {!hydrated ? (
        <HomeOverviewSkeleton />
      ) : (
        <>
          <div id="your-plans">
            <YourPlansSection plans={plans} />
          </div>

          <StartNewPlanSection
            onPlanCreated={addPlan}
            onOpenCustomModal={() => setModalOpen(true)}
          />
        </>
      )}

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
