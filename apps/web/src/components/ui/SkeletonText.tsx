import { Skeleton } from '@/components/ui/Skeleton';

type SkeletonTextProps = {
  lines?: 1 | 2 | 3;
  variant?: 'pulse' | 'shimmer';
  className?: string;
};

const widthPresets = ['w-full', 'w-5/6', 'w-3/4'];

export function SkeletonText({ lines = 1, variant = 'shimmer', className }: SkeletonTextProps) {
  return (
    <div className={['space-y-2', className].filter(Boolean).join(' ')} aria-hidden>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          variant={variant}
          className={`h-4 ${widthPresets[i] ?? 'w-2/3'}`}
          rounded="md"
        />
      ))}
    </div>
  );
}
