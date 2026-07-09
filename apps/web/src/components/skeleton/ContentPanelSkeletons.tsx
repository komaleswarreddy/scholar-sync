import { Skeleton } from '@/components/ui/Skeleton';

export function StudioOutputsSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" aria-busy aria-label="Loading studio outputs">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton-card rounded-xl p-4 space-y-3">
          <Skeleton variant="shimmer" className="h-20 w-full" rounded="lg" />
          <Skeleton variant="shimmer" className="h-3.5 w-2/3" rounded="md" />
        </div>
      ))}
    </div>
  );
}

export function StudyAssetsSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="space-y-3" aria-busy aria-label="Loading study assets">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton-card rounded-xl p-4">
          <Skeleton variant="shimmer" className="h-12 w-full" rounded="lg" />
        </div>
      ))}
    </div>
  );
}
