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
  const { getToken } = useAuth();
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [authLoaded, setAuthLoaded] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Check auth loaded
  useEffect(() => {
    if (getToken) {
      setAuthLoaded(true);
    }
  }, [getToken]);

  // Check if user is admin
  useEffect(() => {
    const checkAdmin = async () => {
      if (!authLoaded || !getToken) {
        return;
      }

      // Ensure token getter is set in API client
      apiClient.setTokenGetter(getToken);

      // Wait a bit for token to be fetched
      await new Promise(resolve => setTimeout(resolve, 1000));

      try {
        // Use silent=true to suppress error logging for expected 403s
        await apiClient.getAggregateMetrics(30, true);
        setIsAdmin(true);
      } catch (error: any) {
        if (error?.response?.status === 403) {
          // Expected 403 for non-admin users
          setIsAdmin(false);
        } else if (error?.response?.status === 401) {
          // Token issue - might need more time
          setTimeout(async () => {
            try {
              await apiClient.getAggregateMetrics(30, true);
              setIsAdmin(true);
            } catch (retryError: any) {
              setIsAdmin(false);
            }
          }, 2000);
        } else {
          setIsAdmin(false);
        }
      }
    };

    if (authLoaded && getToken) {
      checkAdmin();
    }
  }, [authLoaded, getToken]);

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
                isAdmin={isAdmin === true}
              />
            </div>

            {/* Main content area */}
            <main className="flex-1 overflow-y-auto p-4 lg:p-6 min-w-0">
              {isAdmin === null ? (
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
