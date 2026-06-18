'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { LogOut, Shield, User, ChevronDown } from 'lucide-react';
import { useUser } from '@clerk/nextjs';
import { useAppSignOut } from '@/hooks/useAppSignOut';
import { DraftSaveModal } from '../notes/DraftSaveModal';

function getInitials(name: string | null) {
  if (!name) return 'U';
  const parts = name.trim().split(' ');
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  return name[0].toUpperCase();
}

export function UserMenuDropdown() {
  const router = useRouter();
  const pathname = usePathname();
  const { user } = useUser();
  const fullName = user?.fullName ?? null;
  const email = user?.primaryEmailAddress?.emailAddress ?? null;
  const avatarUrl = user?.imageUrl ?? null;
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const isProfileActive = pathname.startsWith('/profile');

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

  const handleProfile = () => {
    setIsOpen(false);
    router.push('/profile/student-info');
  };

  const handleLogout = async () => {
    setIsOpen(false);
    await signOutWithDraftCheck();
  };

  return (
    <>
      <div className="relative" ref={dropdownRef}>
        <button
          type="button"
          onClick={() => setIsOpen((open) => !open)}
          className={`app-user-menu-trigger ${isOpen || isProfileActive ? 'app-user-menu-trigger--active' : ''}`}
          aria-label="Account menu"
          aria-expanded={isOpen}
          aria-haspopup="menu"
        >
          {avatarUrl ? (
            <img
              src={avatarUrl}
              alt={fullName ?? 'User'}
              className="app-user-menu-trigger__avatar"
            />
          ) : (
            <div className="app-user-menu-trigger__avatar app-user-menu-trigger__avatar--fallback">
              {getInitials(fullName)}
            </div>
          )}
          <ChevronDown
            className={`app-user-menu-trigger__chevron ${isOpen ? 'app-user-menu-trigger__chevron--open' : ''}`}
            strokeWidth={2}
          />
        </button>

        {isOpen && (
          <div className="app-user-menu-dropdown" role="menu" aria-label="Account">
            <div className="app-user-menu-dropdown__profile">
              {avatarUrl ? (
                <img
                  src={avatarUrl}
                  alt=""
                  className="app-user-menu-dropdown__avatar"
                />
              ) : (
                <div className="app-user-menu-dropdown__avatar app-user-menu-dropdown__avatar--fallback">
                  {getInitials(fullName)}
                </div>
              )}
              <div className="min-w-0 flex-1">
                <p className="app-user-menu-dropdown__name">{fullName || 'Student'}</p>
                {email ? <p className="app-user-menu-dropdown__email">{email}</p> : null}
              </div>
            </div>

            <div className="app-user-menu-dropdown__actions">
              <button
                type="button"
                role="menuitem"
                onClick={handleProfile}
                className="app-user-menu-dropdown__item"
              >
                <span className="app-user-menu-dropdown__item-icon">
                  <User className="w-4 h-4" strokeWidth={1.75} />
                </span>
                <span>Profile</span>
              </button>

              <Link
                href="/profile/account-security"
                role="menuitem"
                className="app-user-menu-dropdown__item"
                onClick={() => setIsOpen(false)}
              >
                <span className="app-user-menu-dropdown__item-icon">
                  <Shield className="w-4 h-4" strokeWidth={1.75} />
                </span>
                <span>Account & security</span>
              </Link>

              <div className="app-user-menu-dropdown__divider" role="separator" />

              <button
                type="button"
                role="menuitem"
                onClick={handleLogout}
                className="app-user-menu-dropdown__item app-user-menu-dropdown__item--danger"
              >
                <span className="app-user-menu-dropdown__item-icon app-user-menu-dropdown__item-icon--danger">
                  <LogOut className="w-4 h-4" strokeWidth={1.75} />
                </span>
                <span>Sign out</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {draftInfo ? (
        <DraftSaveModal
          isOpen={showDraftModal}
          draftContent={draftInfo.draftContent}
          onSave={handleDraftSave}
          onDiscard={handleDraftDiscard}
          onCancel={handleDraftCancel}
        />
      ) : null}
    </>
  );
}
