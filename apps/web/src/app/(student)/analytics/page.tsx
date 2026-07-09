'use client';

import dynamic from 'next/dynamic';
import { HomeOverviewSkeleton } from '@/components/skeleton';
import { usePortalTabGuard } from '@/hooks/usePortalTabGuard';

const PrepAnalyticsPage = dynamic(
  () => import('@/components/prep-analytics').then((m) => m.PrepAnalyticsPage),
  { loading: () => <HomeOverviewSkeleton /> },
);

export default function AnalyticsPage() {
  const enabled = usePortalTabGuard('analytics');
  if (!enabled) return null;
  return <PrepAnalyticsPage />;
}
