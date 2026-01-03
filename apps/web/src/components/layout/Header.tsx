/**
 * Header Component
 * 
 * Top ribbon with logo, actions, and user menu.
 * Matches NotebookLM design with create notebook, share, settings, analytics.
 */

'use client';

import { 
  Plus, 
  Share2, 
  Settings, 
  BarChart3, 
  User
} from 'lucide-react';
import { Button } from '../ui/Button';

export function Header() {
  const handleCreateNotebook = () => {
    // TODO: Implement create notebook functionality
    alert('Create notebook functionality will be available soon');
  };

  const handleShare = () => {
    // TODO: Implement share functionality
    alert('Share functionality will be available soon');
  };

  const handleSettings = () => {
    // TODO: Navigate to settings page
    alert('Settings page will be available soon');
  };

  const handleAnalytics = () => {
    // TODO: Navigate to analytics page
    alert('Analytics page will be available soon');
  };

  return (
    <header className="h-14 border-b border-border-default flex items-center justify-between px-6 flex-shrink-0" style={{ backgroundColor: '#131314' }}>
      {/* Left Section: Logo + Title */}
      <div className="flex items-center gap-3 flex-1 min-w-0">
        {/* Logo */}
        <div className="w-8 h-8 rounded-xl bg-accent-blue flex items-center justify-center flex-shrink-0">
          <span className="text-background font-bold text-lg">N</span>
        </div>
        
        {/* Title - will be dynamic based on notebook */}
        <h1 className="text-base font-medium text-text-primary truncate">
          Integrated Lean Six Sigma Process Flow Framework
        </h1>
      </div>

      {/* Center Section: Actions */}
      <div className="flex items-center gap-2 flex-shrink-0">
        {/* Create Notebook */}
        <Button
          variant="secondary"
          size="sm"
          onClick={handleCreateNotebook}
          className="flex items-center gap-2 rounded-full"
        >
          <Plus className="w-4 h-4" />
          <span className="hidden sm:inline">Create notebook</span>
        </Button>

        {/* Analytics */}
        <Button
          variant="ghost"
          size="sm"
          onClick={handleAnalytics}
          className="p-2"
          title="Analytics"
        >
          <BarChart3 className="w-4 h-4" />
        </Button>

        {/* Share */}
        <Button
          variant="ghost"
          size="sm"
          onClick={handleShare}
          className="p-2"
          title="Share"
        >
          <Share2 className="w-4 h-4" />
        </Button>

        {/* Settings */}
        <Button
          variant="ghost"
          size="sm"
          onClick={handleSettings}
          className="p-2"
          title="Settings"
        >
          <Settings className="w-4 h-4" />
        </Button>
      </div>

      {/* Right Section: User Avatar */}
      <div className="flex items-center gap-2 flex-shrink-0 ml-4">
        <button
          className="w-8 h-8 rounded-full bg-red-500 flex items-center justify-center text-white font-semibold text-sm hover:opacity-90 transition-opacity"
          title="User menu"
        >
          <User className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}

