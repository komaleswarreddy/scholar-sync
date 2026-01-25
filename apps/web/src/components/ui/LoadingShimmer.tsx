/**
 * Loading Shimmer Component
 * 
 * Shimmer effect for loading states (chat messages).
 * Follows design spec: no spinner, use shimmer skeleton.
 */

export function LoadingShimmer() {
  return (
    <div className="p-4 space-y-2 animate-pulse">
      <div className="h-4 bg-surface rounded w-3/4" />
      <div className="h-4 bg-surface rounded w-full" />
      <div className="h-4 bg-surface rounded w-5/6" />
    </div>
  );
}




