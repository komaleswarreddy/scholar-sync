import { HomeOverviewSkeleton } from '@/components/skeleton';

export default function Loading() {
  return (
    <div className="max-w-7xl mx-auto px-4 md:px-8 pt-8 md:pt-10 pb-6">
      <HomeOverviewSkeleton />
    </div>
  );
}
