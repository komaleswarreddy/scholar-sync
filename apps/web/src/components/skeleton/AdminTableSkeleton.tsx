import { Skeleton } from '@/components/ui/Skeleton';

const STAT_WIDTHS = ['w-16', 'w-20', 'w-14', 'w-24'];
const COL_WIDTHS = ['w-[28%]', 'w-[18%]', 'w-[14%]', 'w-[14%]', 'w-[12%]'];

type AdminTableSkeletonProps = {
  rows?: number;
  showHeader?: boolean;
  showStats?: boolean;
};

/** Premium admin loading state — stat cards, toolbar, and structured table rows. */
export function AdminTableSkeleton({
  rows = 8,
  showHeader = true,
  showStats = true,
}: AdminTableSkeletonProps) {
  return (
    <div
      className="admin-table-skeleton space-y-6"
      aria-busy="true"
      aria-label="Loading admin data"
    >
      {showHeader && (
        <div className="space-y-2.5">
          <Skeleton variant="shimmer" className="h-8 w-52 max-w-full" rounded="lg" />
          <Skeleton variant="shimmer" className="h-4 w-80 max-w-full opacity-70" rounded="md" />
        </div>
      )}

      {showStats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {STAT_WIDTHS.map((width, i) => (
            <div
              key={i}
              className="relative overflow-hidden rounded-2xl border border-border-default/50 bg-modal p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_8px_24px_rgba(15,23,42,0.04)]"
              style={{ animationDelay: `${i * 60}ms` }}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 space-y-3 min-w-0">
                  <Skeleton variant="shimmer" className="h-3 w-20" rounded="md" />
                  <Skeleton variant="shimmer" className={`h-8 ${width}`} rounded="lg" />
                  <Skeleton variant="shimmer" className="h-3 w-24 opacity-60" rounded="md" />
                </div>
                <Skeleton variant="shimmer" className="h-11 w-11 shrink-0" rounded="xl" />
              </div>
              <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-accent-blue/[0.03] via-transparent to-transparent" />
            </div>
          ))}
        </div>
      )}

      <div className="flex flex-col sm:flex-row gap-3">
        <Skeleton variant="shimmer" className="h-11 flex-1 max-w-md" rounded="xl" />
        <div className="flex gap-2">
          <Skeleton variant="shimmer" className="h-11 w-28" rounded="xl" />
          <Skeleton variant="shimmer" className="h-11 w-32" rounded="xl" />
        </div>
      </div>

      <div className="rounded-2xl border border-border-default/60 bg-modal shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_32px_rgba(15,23,42,0.05)] overflow-hidden">
        <div className="grid grid-cols-5 gap-4 px-5 py-3.5 bg-[#f8fafb] border-b border-border-default/50">
          {COL_WIDTHS.map((w, i) => (
            <Skeleton key={`h-${i}`} variant="shimmer" className={`h-3.5 ${w}`} rounded="md" />
          ))}
        </div>
        <div className="divide-y divide-border-default/40">
          {Array.from({ length: rows }).map((_, i) => (
            <div
              key={i}
              className="grid grid-cols-5 gap-4 items-center px-5 py-4"
              style={{ animationDelay: `${i * 40}ms` }}
            >
              <div className="flex items-center gap-3 min-w-0">
                <Skeleton variant="shimmer" className="h-9 w-9 shrink-0" rounded="full" />
                <div className="flex-1 space-y-2 min-w-0">
                  <Skeleton variant="shimmer" className="h-3.5 w-full max-w-[140px]" rounded="md" />
                  <Skeleton variant="shimmer" className="h-3 w-2/3 max-w-[100px] opacity-60" rounded="md" />
                </div>
              </div>
              <Skeleton variant="shimmer" className="h-3.5 w-20" rounded="md" />
              <Skeleton variant="shimmer" className="h-6 w-16" rounded="full" />
              <Skeleton variant="shimmer" className="h-3.5 w-14" rounded="md" />
              <Skeleton variant="shimmer" className="h-8 w-20 ml-auto" rounded="lg" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function AdminDetailSkeleton() {
  return (
    <div className="space-y-5" aria-busy="true" aria-label="Loading details">
      <div className="flex items-center gap-4">
        <Skeleton variant="shimmer" className="h-14 w-14" rounded="full" />
        <div className="space-y-2 flex-1">
          <Skeleton variant="shimmer" className="h-6 w-48" rounded="lg" />
          <Skeleton variant="shimmer" className="h-4 w-64 opacity-70" rounded="md" />
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="rounded-xl border border-border-default/50 bg-modal p-4 space-y-2 shadow-sm"
          >
            <Skeleton variant="shimmer" className="h-3 w-24" rounded="md" />
            <Skeleton variant="shimmer" className="h-5 w-full" rounded="md" />
          </div>
        ))}
      </div>
      <Skeleton variant="shimmer" className="h-36 w-full" rounded="2xl" />
    </div>
  );
}

/** Full admin shell placeholder shown while the platform session is resolving on first paint —
 *  avoids a blank white flash by approximating the sidebar/header layout before it's known
 *  whether the user is signed in. */
export function AdminShellSkeleton() {
  return (
    <div className="flex h-screen bg-background overflow-hidden" aria-busy="true" aria-label="Loading admin console">
      <div className="hidden lg:flex w-64 border-r border-border-default bg-surface flex-col gap-2 p-4">
        <Skeleton variant="shimmer" className="h-8 w-32 mb-4" rounded="lg" />
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} variant="shimmer" className="h-9 w-full" rounded="lg" />
        ))}
      </div>
      <div className="flex-1 flex flex-col min-w-0">
        <div className="h-14 border-b border-border-default flex items-center justify-between px-4 lg:px-6 shrink-0">
          <Skeleton variant="shimmer" className="h-6 w-40" rounded="md" />
          <Skeleton variant="shimmer" className="h-8 w-8" rounded="full" />
        </div>
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          <AdminTableSkeleton />
        </main>
      </div>
    </div>
  );
}

/** Compact inline loader for admin nav transitions — sidebar stays visible. */
export function AdminInlineSkeleton() {
  return (
    <div className="flex items-center justify-center py-24" aria-busy="true">
      <div className="flex flex-col items-center gap-4">
        <div className="relative h-10 w-10">
          <div className="absolute inset-0 rounded-full border-2 border-accent-blue/20" />
          <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-accent-blue animate-spin" />
        </div>
        <p className="text-sm text-text-secondary font-medium">Loading…</p>
      </div>
    </div>
  );
}
