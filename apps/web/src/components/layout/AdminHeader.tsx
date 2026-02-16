'use client';

import { BookOpen } from 'lucide-react';
import { SettingsDropdown } from './SettingsDropdown';
import { UserMenuDropdown } from './UserMenuDropdown';

export function AdminHeader() {
  const notebookTitle = 'NotebookLMSync';

  return (
    <header className="h-14 border-b border-border-default flex items-center justify-between px-6 flex-shrink-0 bg-background">
      {/* Left Section: Logo + Title */}
      <div className="flex items-center gap-3 flex-1 min-w-0">
        {/* Logo - BookOpen icon from lucide-react */}
        <div className="w-8 h-8 rounded-xl bg-accent-blue flex items-center justify-center flex-shrink-0 shadow-sm hover:shadow-md transition-shadow">
          <BookOpen className="w-5 h-5 text-background" />
        </div>

        <h1 className="text-base font-medium text-text-primary truncate" title={notebookTitle}>
          {notebookTitle}
        </h1>
      </div>

      {/* Right Section: Settings + User Menu */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <SettingsDropdown />
        <UserMenuDropdown />
      </div>
    </header>
  );
}
