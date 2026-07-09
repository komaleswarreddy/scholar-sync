import { Skeleton } from '@/components/ui/Skeleton';
import { ChatMessagesSkeleton } from './ChatMessagesSkeleton';

/** Mirrors the 3-column notebook workspace layout (sources / chat / studio)
 * so navigating into a notebook doesn't show a blank flash or bare text
 * while the detail query resolves. */
export function NotebookWorkspaceSkeleton() {
  return (
    <div className="h-screen flex flex-col home-page overflow-hidden" aria-busy aria-label="Loading notebook">
      <div className="h-14 flex-shrink-0 border-b border-[var(--color-home-border)] flex items-center px-5 gap-4">
        <Skeleton variant="shimmer" className="h-6 w-40" rounded="md" />
        <Skeleton variant="shimmer" className="h-6 w-24 ml-auto" rounded="full" />
      </div>
      <div className="flex-1 min-h-0 flex overflow-hidden">
        <div className="w-64 flex-shrink-0 border-r border-[var(--color-home-border)] p-4 space-y-3 hidden md:block">
          <Skeleton variant="shimmer" className="h-4 w-20" rounded="sm" />
          <Skeleton variant="shimmer" className="h-16 w-full" rounded="lg" />
          <Skeleton variant="shimmer" className="h-16 w-full" rounded="lg" />
        </div>
        <div className="flex-1 min-w-0 flex flex-col">
          <div className="h-12 flex-shrink-0 border-b border-[var(--color-home-border)] flex items-center px-4">
            <Skeleton variant="shimmer" className="h-4 w-48" rounded="sm" />
          </div>
          <div className="flex-1 overflow-hidden">
            <ChatMessagesSkeleton count={4} />
          </div>
        </div>
        <div className="w-72 flex-shrink-0 border-l border-[var(--color-home-border)] p-4 space-y-3 hidden lg:block">
          <Skeleton variant="shimmer" className="h-4 w-16" rounded="sm" />
          <div className="grid grid-cols-2 gap-3">
            <Skeleton variant="shimmer" className="h-20 w-full" rounded="lg" />
            <Skeleton variant="shimmer" className="h-20 w-full" rounded="lg" />
          </div>
          <Skeleton variant="shimmer" className="h-4 w-16 mt-4" rounded="sm" />
          <Skeleton variant="shimmer" className="h-12 w-full" rounded="lg" />
        </div>
      </div>
    </div>
  );
}
