'use client';

import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useUser } from '@clerk/nextjs';
import { HomeTopNav } from '@/components/home/HomeTopNav';
import { usePrefetchStudentData } from '@/hooks/usePrefetchStudentData';

const UNDERLINE_ROUTES = ['/library', '/assets', '/analytics', '/study-planner'];

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() ?? '';
  const router = useRouter();
  const { isLoaded, isSignedIn } = useUser();

  usePrefetchStudentData();

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.replace('/sign-in');
    }
  }, [isLoaded, isSignedIn, router]);

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
