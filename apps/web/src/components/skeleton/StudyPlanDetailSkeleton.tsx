import { Skeleton } from '@/components/ui/Skeleton';

/** Matches the study plan detail shape: header + progress card + week calendar + schedule list. */
export function StudyPlanDetailSkeleton() {
  return (
    <div className="space-y-4" aria-busy aria-label="Loading study plan">
      <div className="space-y-3">
        <Skeleton variant="shimmer" className="h-3.5 w-24" rounded="md" />
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-2 flex-1 min-w-0">
            <Skeleton variant="shimmer" className="h-7 w-64 max-w-full" rounded="lg" />
            <div className="flex flex-wrap gap-2">
              <Skeleton variant="shimmer" className="h-6 w-20" rounded="full" />
              <Skeleton variant="shimmer" className="h-6 w-28" rounded="full" />
              <Skeleton variant="shimmer" className="h-6 w-16" rounded="full" />
            </div>
          </div>
          <Skeleton variant="shimmer" className="h-6 w-6 shrink-0" rounded="md" />
        </div>
      </div>

      <div className="skeleton-card rounded-[10px] p-4 flex items-center justify-between gap-5 h-[68px]">
        <div className="space-y-1.5 shrink-0">
          <Skeleton variant="shimmer" className="h-3 w-24" rounded="md" />
          <div className="flex items-center gap-2">
            <Skeleton variant="shimmer" className="h-1 w-[180px]" rounded="full" />
            <Skeleton variant="shimmer" className="h-3 w-8" rounded="md" />
          </div>
        </div>
        <Skeleton variant="shimmer" className="h-3 w-40 flex-1" rounded="md" />
      </div>

      <div className="skeleton-card rounded-xl p-4 space-y-3">
        <Skeleton variant="shimmer" className="h-5 w-32" rounded="md" />
        <Skeleton variant="shimmer" className="h-64 w-full" rounded="lg" />
      </div>

      <div className="space-y-3">
        <Skeleton variant="shimmer" className="h-5 w-40" rounded="md" />
        <div className="space-y-2.5">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton-card rounded-xl p-4">
              <Skeleton variant="shimmer" className="h-10 w-full" rounded="md" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
