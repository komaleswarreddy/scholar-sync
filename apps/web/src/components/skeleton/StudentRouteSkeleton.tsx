'use client';

import { usePathname } from 'next/navigation';
import {
  HomeOverviewSkeleton,
  LibraryGridSkeleton,
  ProfileFormSkeleton,
  NotesListSkeleton,
  StudioOutputsSkeleton,
  StudyAssetsSkeleton,
} from '@/components/skeleton';
import { RouteLoadingSkeleton } from '@/components/ui/RouteLoadingSkeleton';

/** Content-area skeleton while Clerk hydrates (nav shell is already visible). */
export function StudentRouteSkeleton() {
  const pathname = usePathname() ?? '';

  if (pathname.startsWith('/library')) {
    return <LibraryGridSkeleton />;
  }
  if (pathname.startsWith('/profile')) {
    return <ProfileFormSkeleton />;
  }
  if (pathname.startsWith('/notes')) {
    return <NotesListSkeleton />;
  }
  if (pathname.startsWith('/assets')) {
    return <StudyAssetsSkeleton />;
  }
  if (pathname.startsWith('/studios')) {
    return <StudioOutputsSkeleton />;
  }
  if (pathname.startsWith('/analytics')) {
    return <HomeOverviewSkeleton />;
  }
  if (pathname.startsWith('/study-planner') || pathname.startsWith('/problem-solver')) {
    return <RouteLoadingSkeleton variant="home" />;
  }
  if (pathname.startsWith('/home')) {
    return <HomeOverviewSkeleton />;
  }

  return <HomeOverviewSkeleton />;
}
