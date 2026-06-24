'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { TeacherHeader } from '@/components/layout/TeacherHeader';
import { TeacherSidebar } from '@/components/layout/TeacherSidebar';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { hasTeacherSession } from '@/lib/teacher-auth';
import { TeacherExamListSkeleton } from '@/components/skeleton';
import { Menu, X } from 'lucide-react';

const SIDEBAR_COLLAPSED_KEY = 'scholarsync:teacher-sidebar-collapsed:v1';

export default function TeacherLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const isLoginRoute = pathname === '/teacher/login';

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [sessionReady, setSessionReady] = useState(false);

  useEffect(() => {
    setMounted(true);
    try {
      const stored = localStorage.getItem(SIDEBAR_COLLAPSED_KEY);
      if (stored === 'true') setSidebarCollapsed(true);
    } catch {
      // ignore storage errors
    }
  }, []);

  const toggleSidebarCollapsed = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(next));
      } catch {
        // ignore storage errors
      }
      return next;
    });
  };

  useEffect(() => {
    if (!mounted || isLoginRoute) return;

    if (!hasTeacherSession()) {
      router.replace('/teacher/login');
      return;
    }

    setSessionReady(true);
  }, [mounted, isLoginRoute, router]);

  if (isLoginRoute) {
    return <>{children}</>;
  }

  return (
    <ThemeProvider>
      <div
        className="teacher-portal-shell h-screen w-screen flex flex-col overflow-hidden bg-background"
        data-sidebar-collapsed={sidebarCollapsed ? 'true' : 'false'}
      >
        <TeacherHeader />

        <div className="flex-1 flex overflow-hidden min-w-0">
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
            <TeacherSidebar
              collapsed={sidebarCollapsed}
              onToggleCollapse={toggleSidebarCollapsed}
              onNavigate={() => setSidebarOpen(false)}
            />
          </div>

          <main className="flex-1 overflow-y-auto p-4 lg:p-6 min-w-0">
            {!mounted || !sessionReady ? <TeacherExamListSkeleton /> : children}
          </main>
        </div>
      </div>
    </ThemeProvider>
  );
}
