/**
 * Analytics Layout
 * 
 * Full-width layout for the analytics dashboard (no sidebars).
 */

'use client';

import { Header } from '@/components/layout/Header';
import { UserProvider } from '@/contexts/UserContext';
import { ThemeProvider } from '@/contexts/ThemeContext';

export default function AnalyticsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Wrap with both providers to ensure context is available
  // ThemeProvider is needed for SettingsDropdown in Header
  // UserProvider is needed for UserMenuDropdown in Header
  return (
    <ThemeProvider>
      <UserProvider>
        <div className="h-screen w-screen flex flex-col overflow-hidden bg-background">
          <Header />
          <div className="flex-1 overflow-hidden">
            {children}
          </div>
        </div>
      </UserProvider>
    </ThemeProvider>
  );
}
