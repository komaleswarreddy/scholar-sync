'use client';

import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { HomeTopNav } from '@/components/home/HomeTopNav';
import { usePrefetchStudentData } from '@/hooks/usePrefetchStudentData';
import { useUserContext } from '@/contexts/UserContext';
import { hasPlatformSession } from '@/lib/platform-auth';

const UNDERLINE_ROUTES = ['/library', '/assets', '/analytics', '/study-planner'];

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() ?? '';
  const router = useRouter();
  const { loading, isSignedIn } = useUserContext();

  usePrefetchStudentData();

  useEffect(() => {
    if (!loading && !isSignedIn && !hasPlatformSession()) {
      router.replace('/sign-in');
    }
  }, [loading, isSignedIn, router]);

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
