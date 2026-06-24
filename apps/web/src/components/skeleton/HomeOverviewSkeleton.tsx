import { Skeleton } from '@/components/ui/Skeleton';

export function HomeOverviewSkeleton() {
  return (
    <div className="space-y-8" aria-busy aria-label="Loading home overview">
      <div className="space-y-3">
        <Skeleton variant="shimmer" className="h-10 w-72 max-w-full" rounded="lg" />
        <Skeleton variant="shimmer" className="h-5 w-96 max-w-full" rounded="md" />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Skeleton variant="shimmer" className="h-28 w-full" rounded="2xl" />
        <Skeleton variant="shimmer" className="h-28 w-full" rounded="2xl" />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} variant="shimmer" className="h-24 w-full" rounded="2xl" />
        ))}
      </div>

      <Skeleton variant="shimmer" className="h-20 w-full" rounded="2xl" />

      <div className="space-y-3">
        <Skeleton variant="shimmer" className="h-6 w-40" rounded="md" />
        <Skeleton variant="shimmer" className="h-16 w-full" rounded="xl" />
      </div>
    </div>
  );
}
