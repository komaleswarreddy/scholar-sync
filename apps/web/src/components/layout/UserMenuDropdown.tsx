'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { LogOut, Shield, User, ChevronDown } from 'lucide-react';
import { useUserContext } from '@/contexts/UserContext';
import { useAppSignOut } from '@/hooks/useAppSignOut';
import { DraftSaveModal } from '../notes/DraftSaveModal';
import { isSchoolAdmin } from '@/lib/platform-auth';
import { profileDisplayName, profileInitials } from '@/lib/profile-utils';

const ROLE_LABELS: Record<string, string> = {
  teacher: 'Teacher',
  expert: 'Expert',
  schooladmin: 'School Admin',
};

export function UserMenuDropdown() {
  const router = useRouter();
  const pathname = usePathname();
  const { email, role, user, username, loading } = useUserContext();
  const displayName = user ? profileDisplayName(user) : 'User';
  const subtitle = email ?? (username ? `@${username}` : null);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const isProfileActive = pathname.startsWith('/profile');
  const showRoleBadge = role && role !== 'student';

  const {
    signOutWithDraftCheck,
    showDraftModal,
    draftInfo,
    handleDraftSave,
    handleDraftDiscard,
    handleDraftCancel,
  } = useAppSignOut();

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen]);

  const handleLogout = async () => {
    setIsOpen(false);
    await signOutWithDraftCheck();
  };

  return (
    <>
      <div className="relative" ref={dropdownRef}>
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 rounded-full border border-border-default bg-white px-2 py-1.5 hover:bg-surface-hover transition-colors"
          aria-expanded={isOpen}
          aria-haspopup="true"
        >
          <div className="w-8 h-8 rounded-full bg-accent-blue text-white text-sm font-semibold flex items-center justify-center">
            {user ? profileInitials(user) : loading ? '…' : 'U'}
          </div>
          <ChevronDown className={`w-4 h-4 text-text-secondary transition-transform ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {isOpen && (
          <div className="absolute right-0 mt-2 w-64 rounded-xl border border-border-default bg-white shadow-lg z-50 py-2">
            <div className="px-4 py-3 border-b border-border-default">
              <p className="text-sm font-semibold text-text-primary truncate">{displayName}</p>
              {subtitle && <p className="text-xs text-text-secondary truncate mt-0.5">{subtitle}</p>}
              {showRoleBadge && (
                <span className="inline-flex mt-2 rounded-full bg-purple-100 text-purple-700 px-2 py-0.5 text-xs font-medium">
                  {ROLE_LABELS[role] ?? role}
                </span>
              )}
            </div>

            <Link
              href="/profile"
              onClick={() => setIsOpen(false)}
              className={`flex items-center gap-3 px-4 py-2.5 text-sm hover:bg-surface-hover ${
                isProfileActive ? 'text-accent-blue font-medium' : 'text-text-primary'
              }`}
            >
              <User className="w-4 h-4" />
              Profile
            </Link>

            {isSchoolAdmin(user) && (
              <Link
                href="/admin/users"
                onClick={() => setIsOpen(false)}
                className="flex items-center gap-3 px-4 py-2.5 text-sm text-text-primary hover:bg-surface-hover"
              >
                <Shield className="w-4 h-4" />
                Admin dashboard
              </Link>
            )}

            <button
              type="button"
              onClick={handleLogout}
              className="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50"
            >
              <LogOut className="w-4 h-4" />
              Sign out
            </button>
          </div>
        )}
      </div>

      {showDraftModal && draftInfo && (
        <DraftSaveModal
          isOpen={showDraftModal}
          draftContent={draftInfo.draftContent}
          onSave={handleDraftSave}
          onDiscard={handleDraftDiscard}
          onCancel={handleDraftCancel}
        />
      )}
    </>
  );
}
