'use client';

import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { HomeTopNav } from '@/components/home/HomeTopNav';
import { usePrefetchStudentData } from '@/hooks/usePrefetchStudentData';
import { useUserContext } from '@/contexts/UserContext';
import { hasPlatformSession } from '@/lib/platform-auth';

const UNDERLINE_ROUTES = ['/library', '/assets', '/analytics', '/study-planner'];

function clearStaleSessionCookie(): void {
  if (typeof document === 'undefined') return;
  const hasCookie = document.cookie.split('; ').some((c) => c.startsWith('platform_session=1'));
  if (hasCookie && !hasPlatformSession()) {
    document.cookie = 'platform_session=; path=/; max-age=0; expires=Thu, 01 Jan 1970 00:00:00 GMT';
  }
}

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() ?? '';
  const router = useRouter();
  const { loading, isSignedIn } = useUserContext();

  usePrefetchStudentData();

  useEffect(() => {
    clearStaleSessionCookie();
    if (!loading && !isSignedIn && !hasPlatformSession()) {
      router.replace('/sign-in');
    }
  }, [loading, isSignedIn, router]);

  useEffect(() => {
    // Warm the JS chunks for the two "Create notebook" destinations so the
    // first click doesn't pay a cold route-fetch penalty. Safe for the
    // dynamic notebook route: prefetch only fetches the client bundle, it
    // never mounts the page or calls the API for this placeholder slug.
    router.prefetch('/tutor');
    router.prefetch('/notebook/prefetch');
  }, [router]);

  const isProfile = pathname.startsWith('/profile');
  const navStyle = UNDERLINE_ROUTES.some((r) => pathname.startsWith(r)) ? 'underline' : 'pill';
  const hideClassPill = pathname.startsWith('/study-planner');

  return (
    <div className={`min-h-screen flex flex-col home-page ${isProfile ? 'profile-page' : ''}`}>
      <HomeTopNav activeStyle={navStyle} hideClassPill={hideClassPill} />
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}
