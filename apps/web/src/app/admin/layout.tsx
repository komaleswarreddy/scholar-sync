/**
 * Admin ops dashboard layout — standalone admin portal (not Clerk).
 */

'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { AdminHeader } from '@/components/layout/AdminHeader';
import { AdminSidebar } from '@/components/layout/AdminSidebar';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { apiClient } from '@/lib/api-client';
import { hasAdminSession } from '@/lib/admin-auth';
import { Menu, X } from 'lucide-react';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const isLoginRoute = pathname === '/admin/login';

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [sessionReady, setSessionReady] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || isLoginRoute) return;

    if (!hasAdminSession()) {
      router.replace('/admin/login');
      return;
    }

    apiClient.setAdminPortalMode(true);
    setSessionReady(true);
  }, [mounted, isLoginRoute, router]);

  if (isLoginRoute) {
    return <>{children}</>;
  }

  return (
    <ThemeProvider>
      <div className="h-screen w-screen flex flex-col overflow-hidden bg-background">
        <AdminHeader />

        <div className="flex-1 flex overflow-hidden">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="lg:hidden fixed top-16 left-4 z-50 p-2 rounded-lg bg-surface border border-border-default text-text-primary hover:bg-surface-hover transition-colors shadow-md"
            aria-label="Toggle sidebar"
            aria-expanded={sidebarOpen}
          >
            {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>

          {sidebarOpen && (
            <div
              className="lg:hidden fixed inset-0 bg-black/50 z-40"
              onClick={() => setSidebarOpen(false)}
            />
          )}

          <div
            className={`
              fixed lg:static inset-y-0 left-0 z-40 lg:z-auto
              transform transition-transform duration-300 ease-in-out
              ${sidebarOpen ? 'translate-x-0 shadow-xl' : '-translate-x-full lg:translate-x-0'}
            `}
          >
            <AdminSidebar onNavigate={() => setSidebarOpen(false)} />
          </div>

          <main className="flex-1 overflow-y-auto p-4 lg:p-6 min-w-0">
            {!mounted || !sessionReady ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-blue mx-auto mb-4" />
                  <p className="text-text-secondary">Loading...</p>
                </div>
              </div>
            ) : (
              children
            )}
          </main>
        </div>
      </div>
    </ThemeProvider>
  );
}
