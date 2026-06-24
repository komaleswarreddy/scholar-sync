import { Skeleton } from '@/components/ui/Skeleton';

type SkeletonCircleProps = {
  size?: 'sm' | 'md' | 'lg';
  variant?: 'pulse' | 'shimmer';
  className?: string;
};

const sizeMap = {
  sm: 'h-8 w-8',
  md: 'h-10 w-10',
  lg: 'h-12 w-12',
};

export function SkeletonCircle({ size = 'md', variant = 'shimmer', className }: SkeletonCircleProps) {
  return (
    <Skeleton
      variant={variant}
      rounded="full"
      className={[sizeMap[size], className].filter(Boolean).join(' ')}
    />
  );
}
