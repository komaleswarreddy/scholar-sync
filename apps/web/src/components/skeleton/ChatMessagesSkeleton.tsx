import { Skeleton } from '@/components/ui/Skeleton';

export function ChatMessagesSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="p-4 space-y-4" aria-busy aria-label="Loading messages">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className={`flex ${i % 2 === 0 ? 'justify-start' : 'justify-end'}`}
        >
          <div className={`space-y-2 max-w-[75%] ${i % 2 === 0 ? '' : 'items-end'}`}>
            <Skeleton
              variant="shimmer"
              className={`h-16 ${i % 2 === 0 ? 'w-64' : 'w-48'}`}
              rounded="2xl"
            />
          </div>
        </div>
      ))}
    </div>
  );
}
