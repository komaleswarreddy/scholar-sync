/**
 * Analytics Layout
 * 
 * Admin dashboard layout with sidebar navigation and header.
 * Only accessible to admin users.
 */

'use client';

import { useEffect, useState } from 'react';
import { AdminHeader } from '@/components/layout/AdminHeader';
import { AdminSidebar } from '@/components/layout/AdminSidebar';
import { UserProvider } from '@/contexts/UserContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { useAuth } from '@clerk/nextjs';
import { apiClient } from '@/lib/api-client';
import { Menu, X } from 'lucide-react';

export default function AnalyticsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  /** Sidebar only — never block page render on this. */
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  /** Avoid hydration mismatch: Clerk `isLoaded` can differ SSR vs first client render. */
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Best-effort admin check for sidebar (403 from /admin/aggregate is expected for non-admins)
  useEffect(() => {
    if (!isLoaded || !isSignedIn || !getToken) {
      return;
    }
    let cancelled = false;
    apiClient.setTokenGetter(getToken);

    (async () => {
      try {
        const flags = await apiClient.getMyAdminFlags();
        if (!cancelled) setIsAdmin(Boolean(flags?.is_admin));
      } catch {
        if (!cancelled) setIsAdmin(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isLoaded, isSignedIn, getToken]);

  // Don't redirect non-admin users - they can access their own analytics

  // Wrap with both providers to ensure context is available
  // ThemeProvider is needed for SettingsDropdown in Header
  // UserProvider is needed for UserMenuDropdown in Header
  return (
    <ThemeProvider>
      <UserProvider>
        <div className="h-screen w-screen flex flex-col overflow-hidden bg-background">
          {/* Header - Full width at top */}
          <AdminHeader />

          {/* Content area with sidebar and main content */}
          <div className="flex-1 flex overflow-hidden">
            {/* Mobile menu button */}
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden fixed top-16 left-4 z-50 p-2 rounded-lg bg-surface border border-border-default text-text-primary hover:bg-surface-hover transition-colors shadow-md"
              aria-label="Toggle sidebar"
              aria-expanded={sidebarOpen}
            >
              {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>

            {/* Sidebar overlay for mobile */}
            {sidebarOpen && (
              <div
                className="lg:hidden fixed inset-0 bg-black/50 z-40"
                onClick={() => setSidebarOpen(false)}
              />
            )}

            {/* Sidebar */}
            <div
              className={`
                fixed lg:static inset-y-0 left-0 z-40 lg:z-auto
                transform transition-transform duration-300 ease-in-out
                ${sidebarOpen ? 'translate-x-0 shadow-xl' : '-translate-x-full lg:translate-x-0'}
              `}
            >
              <AdminSidebar 
                onNavigate={() => setSidebarOpen(false)} 
                isAdmin={isAdmin}
              />
            </div>

            {/* Main content — show as soon as Clerk token is available (do not wait for admin check) */}
            <main className="flex-1 overflow-y-auto p-4 lg:p-6 min-w-0">
              {!mounted || !isLoaded || !isSignedIn ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-blue mx-auto mb-4"></div>
                    <p className="text-text-secondary">Loading...</p>
                  </div>
                </div>
              ) : (
                children
              )}
            </main>
          </div>
        </div>
      </UserProvider>
    </ThemeProvider>
  );
}
