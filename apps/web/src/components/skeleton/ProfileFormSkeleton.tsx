import { Skeleton } from '@/components/ui/Skeleton';

export function ProfileFormSkeleton() {
  return (
    <div className="flex flex-col md:flex-row gap-8" aria-busy aria-label="Loading profile">
      <div className="w-full md:w-56 space-y-2 shrink-0">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} variant="pulse" className="h-10 w-full" rounded="lg" />
        ))}
      </div>
      <div className="flex-1 space-y-6 min-w-0">
        <Skeleton variant="shimmer" className="h-8 w-48" rounded="md" />
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="space-y-2">
            <Skeleton variant="shimmer" className="h-4 w-28" rounded="md" />
            <Skeleton variant="shimmer" className="h-11 w-full" rounded="lg" />
          </div>
        ))}
      </div>
    </div>
  );
}
