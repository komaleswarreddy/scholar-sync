'use client';

import { useEffect, useRef, useState } from 'react';
import { LogOut, ChevronDown, Shield } from 'lucide-react';
import { useUserContext } from '@/contexts/UserContext';
import { getStoredPlatformUser } from '@/lib/platform-auth';

export function AdminUserMenu() {
  const { signOut } = useUserContext();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const displayLabel =
    getStoredPlatformUser()?.username ||
    getStoredPlatformUser()?.email ||
    'School admin';

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const handleSignOut = () => {
    setIsOpen(false);
    void signOut();
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 rounded-lg border border-border-default bg-surface px-3 py-1.5 text-sm text-text-primary hover:bg-surface-hover"
        aria-expanded={isOpen}
      >
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-accent-blue/10 text-accent-blue">
          <Shield className="h-4 w-4" />
        </span>
        <span className="hidden sm:inline max-w-[140px] truncate">{displayLabel}</span>
        <ChevronDown className="h-4 w-4 text-text-secondary" />
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full z-50 mt-2 w-48 rounded-lg border border-border-default bg-surface py-1 shadow-lg">
          <button
            type="button"
            onClick={handleSignOut}
            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-primary hover:bg-surface-hover"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
