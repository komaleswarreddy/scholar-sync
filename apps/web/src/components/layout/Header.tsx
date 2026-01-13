'use client';

import {
  Plus,
  Share2,
  Settings,
  BarChart3,
  User,
  LogOut
} from 'lucide-react';
import { Button } from '../ui/Button';
import { useUserContext } from '@/contexts/UserContext';

export function Header() {
  const {
    fullName,
    avatarUrl,
    signOut,
  } = useUserContext();

  // ------------------------
  // Actions
  // ------------------------
  const handleCreateNotebook = () => {
    alert('Create notebook functionality will be available soon');
  };

  const handleShare = () => {
    alert('Share functionality will be available soon');
  };

  const handleSettings = () => {
    alert('Settings page will be available soon');
  };

  const handleAnalytics = () => {
    alert('Analytics page will be available soon');
  };

  const handleLogout = async () => {
    await signOut();
  };

  return (
    <header
      className="h-14 border-b border-border-default flex items-center justify-between px-6 flex-shrink-0"
      style={{ backgroundColor: '#131314' }}
    >
      {/* ------------------------
          Left Section: Logo + Title
          ------------------------ */}
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <div className="w-8 h-8 rounded-xl bg-accent-blue flex items-center justify-center flex-shrink-0">
          <span className="text-background font-bold text-lg">N</span>
        </div>

        <h1 className="text-base font-medium text-text-primary truncate">
          Integrated Lean Six Sigma Process Flow Framework
        </h1>
      </div>

      {/* ------------------------
          Center Actions
          ------------------------ */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <Button
          variant="secondary"
          size="sm"
          onClick={handleCreateNotebook}
          className="flex items-center gap-2 rounded-full"
        >
          <Plus className="w-4 h-4" />
          <span className="hidden sm:inline">Create notebook</span>
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={handleAnalytics}
          className="p-2"
          title="Analytics"
        >
          <BarChart3 className="w-4 h-4" />
        </Button>

        <Button
          variant="ghost"
          size="sm"
          onClick={handleShare}
          className="p-2"
          title="Share"
        >
          <Share2 className="w-4 h-4" />
        </Button>

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

      {/* ------------------------
          Right Section: Avatar + Logout
          ------------------------ */}
      <div className="flex items-center gap-2 flex-shrink-0 ml-4">
        {avatarUrl ? (
          <img
            src={avatarUrl}
            alt={fullName ?? 'User'}
            className="w-8 h-8 rounded-full object-cover"
            title={fullName ?? 'User'}
          />
        ) : (
          <div className="w-8 h-8 rounded-full bg-red-500 flex items-center justify-center text-white">
            <User className="w-4 h-4" />
          </div>
        )}

        <Button
          variant="ghost"
          size="sm"
          onClick={handleLogout}
          className="p-2"
          title="Logout"
        >
          <LogOut className="w-4 h-4" />
        </Button>
      </div>
    </header>
  );
}
