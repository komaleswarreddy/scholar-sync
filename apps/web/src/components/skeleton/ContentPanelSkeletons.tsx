import { Skeleton } from '@/components/ui/Skeleton';

export function StudioOutputsSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" aria-busy aria-label="Loading studio outputs">
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} variant="shimmer" className="h-36 w-full" rounded="xl" />
      ))}
    </div>
  );
}

export function StudyAssetsSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="space-y-3" aria-busy aria-label="Loading study assets">
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} variant="shimmer" className="h-20 w-full" rounded="xl" />
      ))}
    </div>
  );
}
