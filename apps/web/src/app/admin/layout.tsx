/**
 * Admin ops dashboard layout — requires schooladmin platform session.
 */

'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { AdminHeader } from '@/components/layout/AdminHeader';
import { AdminSidebar } from '@/components/layout/AdminSidebar';
import { ThemeProvider } from '@/contexts/ThemeContext';
import {
  getPlatformToken,
  getStoredPlatformUser,
  hasPlatformSession,
  isSchoolAdmin,
} from '@/lib/platform-auth';
import { usePlatformSession } from '@/hooks/usePlatformSession';
import { usePrefetchAdminData, primeAdminApiToken } from '@/hooks/usePrefetchAdminData';
import { AdminShellSkeleton } from '@/components/skeleton';
import { Menu, X } from 'lucide-react';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const isLoginRoute = pathname === '/admin/login';
  const session = usePlatformSession();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  usePrefetchAdminData();

  useEffect(() => {
    if (session.signedIn && isSchoolAdmin(session.user, session.token)) {
      primeAdminApiToken();
    }
  }, [session.signedIn, session.user, session.token]);

  useEffect(() => {
    if (isLoginRoute) {
      router.replace('/sign-in');
      return;
    }
    if (!hasPlatformSession()) {
      router.replace('/sign-in');
      return;
    }
    const user = session.user ?? getStoredPlatformUser();
    const token = session.token ?? getPlatformToken();
    if (!isSchoolAdmin(user, token)) {
      router.replace('/home');
    }
  }, [isLoginRoute, router, session.user, session.token, session.signedIn]);

  if (isLoginRoute) {
    return null;
  }

  // Session resolution reads sessionStorage, which isn't available until after hydration —
  // render a skeleton shell instead of blanking the page while that's still unknown. Only
  // treat `signedIn: false` as definitive once `isHydrated` confirms it (see usePlatformSession).
  if (!session.isHydrated) {
    return (
      <ThemeProvider>
        <AdminShellSkeleton />
      </ThemeProvider>
    );
  }

  if (!session.signedIn) {
    return null;
  }

  return (
    <ThemeProvider>
      <div className="flex h-screen bg-background overflow-hidden">
        <div
          className={`fixed inset-0 z-40 bg-black/50 lg:hidden transition-opacity ${
            sidebarOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
          }`}
          onClick={() => setSidebarOpen(false)}
        />
        <div
          className={`fixed inset-y-0 left-0 z-50 w-64 transform transition-transform lg:relative lg:translate-x-0 ${
            sidebarOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
        >
          <AdminSidebar onNavigate={() => setSidebarOpen(false)} />
        </div>

        <div className="flex-1 flex flex-col min-w-0">
          <AdminHeader />
          <main className="flex-1 overflow-y-auto p-4 lg:p-6">{children}</main>
        </div>

        <button
          type="button"
          className="fixed bottom-4 right-4 z-50 lg:hidden p-3 rounded-full bg-accent-blue text-white shadow-lg"
          onClick={() => setSidebarOpen((o) => !o)}
          aria-label="Toggle menu"
        >
          {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>
    </ThemeProvider>
  );
}
