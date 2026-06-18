type RouteLoadingVariant = 'default' | 'home' | 'dashboard' | 'admin';

function PulseBar({ className }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-border-default/60 ${className ?? ''}`} />;
}

export function RouteLoadingSkeleton({ variant = 'default' }: { variant?: RouteLoadingVariant }) {
  if (variant === 'dashboard') {
    return (
      <div className="h-screen w-screen flex flex-col overflow-hidden bg-background p-4 gap-4">
        <PulseBar className="h-14 w-full rounded-2xl" />
        <div className="flex-1 flex gap-4 min-h-0">
          <PulseBar className="w-[18%] h-full rounded-3xl" />
          <PulseBar className="flex-1 h-full rounded-3xl" />
          <PulseBar className="w-[18%] h-full rounded-3xl" />
        </div>
      </div>
    );
  }

  if (variant === 'admin') {
    return (
      <div className="flex h-screen bg-background">
        <PulseBar className="hidden lg:block w-64 h-full rounded-none" />
        <div className="flex-1 flex flex-col min-w-0">
          <PulseBar className="h-16 w-full rounded-none" />
          <div className="flex-1 p-6 space-y-4">
            <PulseBar className="h-8 w-48" />
            <PulseBar className="h-64 w-full rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  if (variant === 'home') {
    return (
      <div className="min-h-screen home-page">
        <PulseBar className="h-16 w-full rounded-none" />
        <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
          <PulseBar className="h-10 w-64" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <PulseBar key={i} className="h-24 rounded-2xl" />
            ))}
          </div>
          <PulseBar className="h-40 w-full rounded-2xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-4 p-8">
      <div className="h-10 w-10 animate-spin rounded-full border-2 border-border-default border-t-primary" />
      <PulseBar className="h-4 w-32" />
    </div>
  );
}
