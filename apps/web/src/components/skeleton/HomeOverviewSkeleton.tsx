import { Skeleton } from '@/components/ui/Skeleton';

export function HomeOverviewSkeleton() {
  return (
    <div className="space-y-8" aria-busy aria-label="Loading home overview">
      <div className="space-y-3">
        <Skeleton variant="shimmer" className="h-10 w-72 max-w-full" rounded="lg" />
        <Skeleton variant="shimmer" className="h-5 w-96 max-w-full" rounded="md" />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="skeleton-card rounded-2xl p-5 space-y-3">
          <Skeleton variant="shimmer" className="h-4 w-24" rounded="md" />
          <Skeleton variant="shimmer" className="h-6 w-40" rounded="md" />
        </div>
        <div className="skeleton-card rounded-2xl p-5 space-y-3">
          <Skeleton variant="shimmer" className="h-4 w-32" rounded="md" />
          <Skeleton variant="shimmer" className="h-6 w-36" rounded="md" />
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="skeleton-card rounded-2xl p-4 space-y-2.5">
            <Skeleton variant="shimmer" className="h-3 w-16" rounded="md" />
            <Skeleton variant="shimmer" className="h-6 w-12" rounded="md" />
          </div>
        ))}
      </div>

      <div className="skeleton-card rounded-2xl p-5">
        <Skeleton variant="shimmer" className="h-full w-full min-h-[3rem]" rounded="lg" />
      </div>

      <div className="space-y-3">
        <Skeleton variant="shimmer" className="h-6 w-40" rounded="md" />
        <div className="skeleton-card rounded-xl p-4">
          <Skeleton variant="shimmer" className="h-8 w-full" rounded="md" />
        </div>
      </div>
    </div>
  );
}
