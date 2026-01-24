/**
 * Source Item Skeleton Component
 * 
 * Loading skeleton for source items during initial load.
 */

export function SourceItemSkeleton() {
  return (
    <div className="flex items-start gap-3 p-3 rounded-xl border border-transparent animate-pulse">
      <div className="mt-0.5">
        <div className="w-4 h-4 rounded bg-surface-hover" />
      </div>
      
      <div className="flex-1 min-w-0 space-y-2">
        {/* Status badge skeleton */}
        <div className="h-5 w-20 rounded bg-surface-hover" />
        
        {/* Title skeleton */}
        <div className="h-4 w-3/4 rounded bg-surface-hover" />
        
        {/* Metadata skeleton */}
        <div className="flex items-center gap-2">
          <div className="h-3 w-16 rounded bg-surface-hover" />
          <div className="h-3 w-1 rounded-full bg-surface-hover" />
          <div className="h-3 w-20 rounded bg-surface-hover" />
        </div>
      </div>
      
      <div className="w-6 h-6 rounded-lg bg-surface-hover" />
    </div>
  );
}
