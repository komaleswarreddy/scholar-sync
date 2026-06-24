import { Skeleton } from '@/components/ui/Skeleton';

export type RouteLoadingVariant =
  | 'default'
  | 'home'
  | 'dashboard'
  | 'admin'
  | 'teacher'
  | 'profile';

export function RouteLoadingSkeleton({ variant = 'default' }: { variant?: RouteLoadingVariant }) {
  if (variant === 'dashboard') {
    return (
      <div className="h-screen w-screen flex flex-col overflow-hidden bg-background p-4 gap-4">
        <Skeleton variant="pulse" className="h-14 w-full" rounded="2xl" />
        <div className="flex-1 flex gap-4 min-h-0">
          <Skeleton variant="pulse" className="w-[18%] h-full" rounded="3xl" />
          <Skeleton variant="pulse" className="flex-1 h-full" rounded="3xl" />
          <Skeleton variant="pulse" className="w-[18%] h-full" rounded="3xl" />
        </div>
      </div>
    );
  }

  if (variant === 'admin') {
    return (
      <div className="flex h-screen bg-background">
        <Skeleton variant="pulse" className="hidden lg:block w-64 h-full" rounded="none" />
        <div className="flex-1 flex flex-col min-w-0">
          <Skeleton variant="pulse" className="h-16 w-full" rounded="none" />
          <div className="flex-1 p-6 space-y-4">
            <Skeleton variant="pulse" className="h-8 w-48" rounded="md" />
            <Skeleton variant="pulse" className="h-64 w-full" rounded="xl" />
          </div>
        </div>
      </div>
    );
  }

  if (variant === 'teacher') {
    return (
      <div className="flex h-screen bg-background">
        <Skeleton variant="pulse" className="hidden lg:block w-56 h-full" rounded="none" />
        <div className="flex-1 flex flex-col min-w-0">
          <Skeleton variant="pulse" className="h-14 w-full" rounded="none" />
          <div className="flex-1 p-6 space-y-4 max-w-5xl">
            <Skeleton variant="pulse" className="h-8 w-40" rounded="md" />
            <Skeleton variant="shimmer" className="h-12 w-full" rounded="lg" />
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} variant="shimmer" className="h-16 w-full" rounded="xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (variant === 'profile') {
    return (
      <div className="min-h-screen home-page">
        <Skeleton variant="pulse" className="h-16 w-full" rounded="none" />
        <div className="max-w-6xl mx-auto px-4 py-8 flex flex-col md:flex-row gap-8">
          <div className="w-full md:w-56 space-y-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} variant="pulse" className="h-10 w-full" rounded="lg" />
            ))}
          </div>
          <div className="flex-1 space-y-6">
            <Skeleton variant="shimmer" className="h-8 w-48" rounded="md" />
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="space-y-2">
                <Skeleton variant="shimmer" className="h-4 w-24" rounded="md" />
                <Skeleton variant="shimmer" className="h-11 w-full" rounded="lg" />
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (variant === 'home') {
    return (
      <div className="min-h-screen home-page">
        <Skeleton variant="pulse" className="h-16 w-full" rounded="none" />
        <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
          <Skeleton variant="pulse" className="h-10 w-64" rounded="md" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} variant="pulse" className="h-24" rounded="2xl" />
            ))}
          </div>
          <Skeleton variant="pulse" className="h-40 w-full" rounded="2xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-4 p-8">
      <div className="h-10 w-10 animate-spin rounded-full border-2 border-border-default border-t-brand-primary" />
      <Skeleton variant="pulse" className="h-4 w-32" rounded="md" />
    </div>
  );
}
