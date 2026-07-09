'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUserContext } from '@/contexts/UserContext';
import { usePlatformSession } from '@/hooks/usePlatformSession';
import {
  HomeHero,
  QuickActionCard,
  FocusThisWeekCard,
  OverviewMetricCard,
  ContinueLearningRow,
  HomeBottomBanner,
  HomeMobileNav,
} from '@/components/home';
import { CreateNotebookPopover } from '@/components/home/CreateNotebookPopover';
import { HomeOverviewSkeleton } from '@/components/skeleton';
import { useHomeSummary } from '@/hooks/useHomeSummary';
import { profileGreetingName } from '@/lib/profile-utils';
import { mapHomeOverviewMetrics } from '@/lib/home-mapper';
import { track } from '@/lib/telemetry';

export default function HomeLandingPage() {
  const router = useRouter();
  const { user: contextUser } = useUserContext();
  const { user: sessionUser } = usePlatformSession();
  const user = contextUser ?? sessionUser;
  const [createPopoverOpen, setCreatePopoverOpen] = useState(false);
  const { data: homeSummary, isPending: homePending } = useHomeSummary();

  useEffect(() => {
    track('home.viewed');
  }, []);

  const firstName = useMemo(() => profileGreetingName(user), [user]);

  const overviewMetrics = useMemo(
    () => (homeSummary ? mapHomeOverviewMetrics(homeSummary) : []),
    [homeSummary],
  );

  const recentNotebook = useMemo(() => {
    const fromSummary = homeSummary?.continue_learning?.[0];
    if (fromSummary?.title && fromSummary?.slug) {
      return { title: fromSummary.title, slug: fromSummary.slug };
    }
    return null;
  }, [homeSummary?.continue_learning]);

  const continueDescription = useMemo(() => {
    if (homePending && !homeSummary) return '\u00a0';
    if (recentNotebook?.title) return recentNotebook.title;
    return 'No recent notebook yet';
  }, [homePending, homeSummary, recentNotebook?.title]);

  const handleContinue = () => {
    track('home.continue_learning_clicked');
    if (recentNotebook?.slug) {
      router.push(`/notebook/${recentNotebook.slug}`);
      return;
    }
    router.push('/library');
  };

  return (
    <div className="max-w-7xl mx-auto px-4 md:px-8 pt-8 md:pt-10 pb-10">
      <HomeMobileNav />

      {homePending && !homeSummary ? (
        <HomeOverviewSkeleton />
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_340px] xl:grid-cols-[minmax(0,1fr)_380px] gap-5 lg:gap-6 mb-8 items-stretch mt-2 md:mt-4">
            <div className="min-w-0 flex flex-col h-full min-h-0">
              <HomeHero
                greetingName={firstName}
                performanceLine={
                  homeSummary?.performance_line ||
                  'Create a notebook and start studying to see personalized insights.'
                }
                className="flex-1 min-h-0"
              />

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4 md:mt-5 flex-shrink-0">
                <QuickActionCard
                  tone="continue"
                  title="Continue"
                  description={continueDescription}
                  onClick={handleContinue}
                />
                <div>
                  <CreateNotebookPopover
                    open={createPopoverOpen}
                    onClose={() => setCreatePopoverOpen(false)}
                    onCreated={(notebookSlug) => router.push(`/notebook/${notebookSlug}`)}
                  />
                  <QuickActionCard
                    tone="notebook"
                    title="Create Notebook"
                    description="Start a new notebook"
                    isActive={createPopoverOpen}
                    onClick={() => {
                      track('home.create_notebook_clicked');
                      setCreatePopoverOpen(true);
                    }}
                  />
                </div>
              </div>
            </div>

            <div className="hidden lg:flex min-w-0 w-full h-full min-h-0">
              <FocusThisWeekCard focus={homeSummary?.focus_concept} />
            </div>
          </div>

          <div className="lg:hidden mb-6">
            <FocusThisWeekCard focus={homeSummary?.focus_concept} />
          </div>

          <section className="mb-6">
            <h3 className="home-section-label mb-4">Overview of learning</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {overviewMetrics.map((m) => (
                <OverviewMetricCard key={m.id} metric={m} />
              ))}
            </div>
          </section>

          <ContinueLearningRow items={homeSummary?.continue_learning ?? []} />

          <HomeBottomBanner />
        </>
      )}
    </div>
  );
}
