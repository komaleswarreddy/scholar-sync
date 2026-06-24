'use client';

import dynamic from 'next/dynamic';
import { HomeOverviewSkeleton } from '@/components/skeleton';

const PrepAnalyticsPage = dynamic(
  () => import('@/components/prep-analytics').then((m) => m.PrepAnalyticsPage),
  { loading: () => <HomeOverviewSkeleton /> },
);

export default function AnalyticsPage() {
  return <PrepAnalyticsPage />;
}
