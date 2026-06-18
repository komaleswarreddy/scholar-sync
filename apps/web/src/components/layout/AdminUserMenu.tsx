'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { LogOut, ChevronDown, Shield } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { clearAdminSession } from '@/lib/admin-auth';

export function AdminUserMenu() {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const handleExitAdmin = () => {
    setIsOpen(false);
    clearAdminSession();
    apiClient.clearAuthSession();
    router.push('/admin/login');
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
        <span className="hidden sm:inline max-w-[140px] truncate">sync@gmail.com</span>
        <ChevronDown className="h-4 w-4 text-text-secondary" />
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full z-50 mt-2 w-48 rounded-lg border border-border-default bg-surface py-1 shadow-lg">
          <button
            type="button"
            onClick={handleExitAdmin}
            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-primary hover:bg-surface-hover"
          >
            <LogOut className="h-4 w-4" />
            Exit admin
          </button>
        </div>
      )}
    </div>
  );
}
