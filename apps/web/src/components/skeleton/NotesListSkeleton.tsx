import { Skeleton } from '@/components/ui/Skeleton';
import { SkeletonText } from '@/components/ui/SkeletonText';

export function NotesListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-3" aria-busy aria-label="Loading notes">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="skeleton-card p-4 rounded-xl space-y-2"
        >
          <Skeleton variant="shimmer" className="h-5 w-2/3" rounded="md" />
          <SkeletonText lines={2} />
          <Skeleton variant="shimmer" className="h-3 w-24" rounded="md" />
        </div>
      ))}
    </div>
  );
}
