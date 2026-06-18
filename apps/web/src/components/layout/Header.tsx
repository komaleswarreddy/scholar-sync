'use client';

import {
  Plus,
  Share2,
  BarChart3,
  BookOpen,
  Home,
  GraduationCap,
} from 'lucide-react';
import { useRouter, usePathname } from 'next/navigation';
import { Button } from '../ui/Button';
import { SettingsDropdown } from './SettingsDropdown';
import { UserMenuDropdown } from './UserMenuDropdown';

export function Header() {
  const router = useRouter();
  const pathname = usePathname();
  const isAnalyticsPage = pathname === '/analytics';
  const isDashboardPage = pathname === '/dashboard';
  const isHomePage = pathname === '/home';
  const isTutorModePage = pathname === '/tutor-mode' || pathname === '/tutor';
  // Temporary: Static title - will be made dynamic with user input later
  const notebookTitle = 'NotebookLMSync';

  // ------------------------
  // Actions
  // ------------------------
  const handleCreateNotebook = () => {
    alert('Create notebook functionality will be available soon');
  };

  const handleShare = () => {
    alert('Share functionality will be available soon');
  };

  const handleAnalytics = () => {
    router.push('/analytics');
  };

  const handleHome = () => {
    router.push('/home');
  };

  const handleTutorMode = () => {
    router.push('/tutor');
  };

  return (
    <header
      className="h-14 border-b border-border-default flex items-center justify-between px-6 flex-shrink-0 bg-background"
    >
      {/* ------------------------
          Left Section: Logo + Title
          ------------------------ */}
      <div className="flex items-center gap-3 flex-1 min-w-0">
        {/* Temporary Logo - BookOpen icon from lucide-react */}
        <div className="w-8 h-8 rounded-xl bg-accent-blue flex items-center justify-center flex-shrink-0 shadow-sm hover:shadow-md transition-shadow">
          <BookOpen className="w-5 h-5 text-background" />
        </div>

        <h1 className="text-base font-medium text-text-primary truncate" title={notebookTitle}>
          {notebookTitle}
        </h1>
      </div>

      {/* ------------------------
          Center Actions
          ------------------------ */}
      <div className="flex items-center gap-2 flex-shrink-0 mx-4">
        <Button
          variant="secondary"
          size="sm"
          onClick={handleCreateNotebook}
          className="flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          <span className="hidden sm:inline">Create notebook</span>
        </Button>

        {isDashboardPage ? (
          <Button
            variant="secondary"
            size="sm"
            onClick={handleTutorMode}
            className="flex items-center gap-2"
          >
            <GraduationCap className="w-4 h-4" />
            <span className="hidden sm:inline">Tutor Mode</span>
          </Button>
        ) : isHomePage ? (
          <Button
            variant="secondary"
            size="sm"
            onClick={handleTutorMode}
            className="flex items-center gap-2"
          >
            <GraduationCap className="w-4 h-4" />
            <span className="hidden sm:inline">Tutor Mode</span>
          </Button>
        ) : null}

        {/* Show Home button on analytics page, Analytics button on dashboard/home */}
        {isAnalyticsPage || isTutorModePage ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleHome}
            className="p-2"
            title="Home"
            aria-label="Home"
          >
            <Home className="w-4 h-4" />
          </Button>
        ) : (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleAnalytics}
            className="p-2"
            title="Analytics"
            aria-label="Analytics"
          >
            <BarChart3 className="w-4 h-4" />
          </Button>
        )}

        <Button
          variant="ghost"
          size="sm"
          onClick={handleShare}
          className="p-2"
          title="Share"
          aria-label="Share"
        >
          <Share2 className="w-4 h-4" />
        </Button>

        <SettingsDropdown />
      </div>

      {/* ------------------------
          Right Section: User Menu
          ------------------------ */}
      <div className="flex items-center flex-shrink-0">
        <UserMenuDropdown />
      </div>
    </header>
  );
}
