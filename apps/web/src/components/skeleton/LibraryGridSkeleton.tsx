import { Skeleton } from '@/components/ui/Skeleton';
import { SkeletonCircle } from '@/components/ui/SkeletonCircle';
import { SkeletonText } from '@/components/ui/SkeletonText';

function NotebookCardSkeleton() {
  return (
    <article className="library-notebook-card p-5 space-y-3">
      <div className="flex items-start justify-between gap-2">
        <Skeleton variant="shimmer" className="h-3 w-28" rounded="md" />
        <div className="flex items-center gap-2">
          <SkeletonCircle size="sm" />
          <Skeleton variant="shimmer" className="h-3 w-16" rounded="md" />
        </div>
      </div>
      <Skeleton variant="shimmer" className="h-6 w-4/5" rounded="md" />
      <SkeletonText lines={2} />
      <div className="flex gap-3 pt-1">
        <Skeleton variant="shimmer" className="h-5 w-14" rounded="full" />
        <Skeleton variant="shimmer" className="h-5 w-14" rounded="full" />
        <Skeleton variant="shimmer" className="h-5 w-14" rounded="full" />
      </div>
    </article>
  );
}

export function LibraryGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div
      className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5"
      aria-busy
      aria-label="Loading notebooks"
    >
      {Array.from({ length: count }).map((_, i) => (
        <NotebookCardSkeleton key={i} />
      ))}
    </div>
  );
}
