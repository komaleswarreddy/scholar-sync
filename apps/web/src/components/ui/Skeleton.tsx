export type SkeletonVariant = 'pulse' | 'shimmer';

type SkeletonProps = {
  variant?: SkeletonVariant;
  className?: string;
  rounded?: 'none' | 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl' | 'full';
};

const roundedMap = {
  none: 'rounded-none',
  sm: 'rounded-sm',
  md: 'rounded-md',
  lg: 'rounded-lg',
  xl: 'rounded-xl',
  '2xl': 'rounded-2xl',
  '3xl': 'rounded-3xl',
  full: 'rounded-full',
};

function cx(...parts: (string | undefined | false)[]) {
  return parts.filter(Boolean).join(' ');
}

export function Skeleton({ variant = 'pulse', className, rounded = 'md' }: SkeletonProps) {
  if (variant === 'shimmer') {
    // Opaque base fill (not an alpha-blended tint) so the shape always reads
    // as a distinct card silhouette against light page backgrounds instead
    // of blending into them; the sweep overlay adds the "loading" motion.
    return (
      <div
        className={cx('relative isolate overflow-hidden bg-border-default skeleton-sweep', roundedMap[rounded], className)}
        aria-hidden
      />
    );
  }

  return (
    <div
      className={cx('animate-pulse bg-border-default', roundedMap[rounded], className)}
      aria-hidden
    />
  );
}
