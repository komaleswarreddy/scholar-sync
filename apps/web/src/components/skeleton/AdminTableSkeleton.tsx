import { Skeleton } from '@/components/ui/Skeleton';

export function AdminTableSkeleton({ rows = 8 }: { rows?: number }) {
  return (
    <div className="space-y-6 p-6" aria-busy aria-label="Loading admin data">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} variant="shimmer" className="h-20 w-full" rounded="xl" />
        ))}
      </div>
      <div className="flex gap-3">
        <Skeleton variant="shimmer" className="h-10 flex-1 max-w-xs" rounded="lg" />
        <Skeleton variant="shimmer" className="h-10 w-32" rounded="lg" />
      </div>
      <div className="rounded-xl border border-border-default overflow-hidden">
        <Skeleton variant="pulse" className="h-11 w-full" rounded="none" />
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} variant="shimmer" className="h-12 w-full border-t border-border-default/50" rounded="none" />
        ))}
      </div>
    </div>
  );
}

export function AdminDetailSkeleton() {
  return (
    <div className="space-y-4 p-4" aria-busy aria-label="Loading user details">
      <Skeleton variant="shimmer" className="h-8 w-40" rounded="md" />
      <div className="grid grid-cols-2 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} variant="shimmer" className="h-16 w-full" rounded="lg" />
        ))}
      </div>
      <Skeleton variant="shimmer" className="h-32 w-full" rounded="xl" />
    </div>
  );
}
