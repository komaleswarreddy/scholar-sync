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
    return (
      <div
        className={cx(
          'bg-gradient-to-r from-border-default/40 via-border-default/70 to-border-default/40',
          'bg-[length:200%_100%] animate-shimmer',
          roundedMap[rounded],
          className,
        )}
        aria-hidden
      />
    );
  }

  return (
    <div
      className={cx('animate-pulse bg-border-default/60', roundedMap[rounded], className)}
      aria-hidden
    />
  );
}
