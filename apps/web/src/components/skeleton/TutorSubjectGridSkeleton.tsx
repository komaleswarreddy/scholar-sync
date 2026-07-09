import { Skeleton } from '@/components/ui/Skeleton';

function SubjectCardSkeleton() {
  return (
    <div className="skeleton-card rounded-2xl p-5 space-y-3 min-h-[136px]">
      <Skeleton variant="shimmer" className="h-10 w-10" rounded="xl" />
      <Skeleton variant="shimmer" className="h-5 w-3/4" rounded="md" />
      <Skeleton variant="shimmer" className="h-3.5 w-1/2" rounded="md" />
    </div>
  );
}

/** Matches the Tutor Mode landing shape: page title + subject picker grid. */
export function TutorSubjectGridSkeleton({ count = 8 }: { count?: number }) {
  return (
    <div className="space-y-8" aria-busy aria-label="Loading tutor mode">
      <div className="space-y-3">
        <Skeleton variant="shimmer" className="h-9 w-52 max-w-full" rounded="lg" />
        <Skeleton variant="shimmer" className="h-5 w-96 max-w-full" rounded="md" />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: count }).map((_, i) => (
          <SubjectCardSkeleton key={i} />
        ))}
      </div>
    </div>
  );
}
