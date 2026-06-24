import { Skeleton } from '@/components/ui/Skeleton';

export function TeacherExamListSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-4" aria-busy aria-label="Loading exams">
      <div className="flex justify-between items-center gap-4">
        <Skeleton variant="shimmer" className="h-8 w-36" rounded="md" />
        <Skeleton variant="shimmer" className="h-10 w-32" rounded="lg" />
      </div>
      <Skeleton variant="shimmer" className="h-11 w-full" rounded="lg" />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} variant="shimmer" className="h-16 w-full" rounded="xl" />
      ))}
    </div>
  );
}

export function TeacherAnalyticsSkeleton() {
  return (
    <div className="space-y-6" aria-busy aria-label="Loading analytics">
      <Skeleton variant="shimmer" className="h-8 w-48" rounded="md" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} variant="shimmer" className="h-24 w-full" rounded="xl" />
        ))}
      </div>
      <Skeleton variant="shimmer" className="h-64 w-full" rounded="xl" />
    </div>
  );
}

export function TeacherWizardSkeleton() {
  return (
    <div className="space-y-6 max-w-2xl" aria-busy aria-label="Loading exam wizard">
      <Skeleton variant="shimmer" className="h-6 w-full max-w-md" rounded="md" />
      <Skeleton variant="shimmer" className="h-10 w-full" rounded="lg" />
      <Skeleton variant="shimmer" className="h-32 w-full" rounded="xl" />
      <div className="flex gap-3 justify-end">
        <Skeleton variant="pulse" className="h-10 w-24" rounded="lg" />
        <Skeleton variant="pulse" className="h-10 w-24" rounded="lg" />
      </div>
    </div>
  );
}
