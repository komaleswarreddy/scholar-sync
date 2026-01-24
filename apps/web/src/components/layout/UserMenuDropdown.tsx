'use client';

import { useState, useRef, useEffect } from 'react';
import { User, LogOut, ChevronDown } from 'lucide-react';
import { useUserContext } from '@/contexts/UserContext';
import { checkForNoteDrafts, removeDraft } from '@/lib/note-draft-utils';
import { DraftSaveModal } from '../notes/DraftSaveModal';

export function UserMenuDropdown() {
  const { fullName, email, avatarUrl, signOut } = useUserContext();
  const [isOpen, setIsOpen] = useState(false);
  const [showDraftModal, setShowDraftModal] = useState(false);
  const [draftInfo, setDraftInfo] = useState<{
    draftKey: string;
    draftContent: string;
  } | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
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

  // Close dropdown on Escape key
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
    
    // Check for unsaved note drafts before logging out
    const { hasDraft, draftKey, draftContent } = checkForNoteDrafts();
    
    if (hasDraft && draftContent && draftKey) {
      // Show modal with save/discard options
      setDraftInfo({ draftKey, draftContent });
      setShowDraftModal(true);
    } else {
      // No draft, proceed with logout
      await signOut();
    }
  };

  const handleDraftSave = () => {
    // Draft was saved as note, remove it from localStorage
    if (draftInfo) {
      removeDraft(draftInfo.draftKey);
    }
    setShowDraftModal(false);
    setDraftInfo(null);
    // Proceed with logout after saving
    signOut();
  };

  const handleDraftDiscard = () => {
    // User chose to discard - remove draft and logout
    if (draftInfo) {
      removeDraft(draftInfo.draftKey);
    }
    setShowDraftModal(false);
    setDraftInfo(null);
    signOut();
  };

  const handleDraftCancel = () => {
    // User cancelled - don't logout, just close modal
    setShowDraftModal(false);
    setDraftInfo(null);
  };

  const handleProfile = () => {
    setIsOpen(false);
    // TODO: Navigate to profile page or open profile modal
    alert('Profile page will be available soon');
  };


  const getInitials = (name: string | null) => {
    if (!name) return 'U';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return name[0].toUpperCase();
  };

  return (
    <>
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-surface-hover transition-colors focus:outline-none focus:ring-2 focus:ring-accent-blue focus:ring-offset-2 focus:ring-offset-background"
          aria-label="User menu"
          aria-expanded={isOpen}
          aria-haspopup="true"
        >
          {avatarUrl ? (
            <img
              src={avatarUrl}
              alt={fullName ?? 'User'}
              className="w-8 h-8 rounded-full object-cover border-2 border-transparent hover:border-border-active transition-colors"
              title={fullName ?? 'User'}
            />
          ) : (
            <div className="w-8 h-8 rounded-full bg-accent-blue flex items-center justify-center text-background font-semibold text-sm border-2 border-transparent hover:border-border-active transition-colors">
              {getInitials(fullName)}
            </div>
          )}
          <ChevronDown
            className={`w-4 h-4 text-text-secondary transition-transform ${
              isOpen ? 'transform rotate-180' : ''
            }`}
          />
        </button>

        {isOpen && (
          <div className="absolute right-0 top-full mt-2 w-64 bg-modal border border-border-default rounded-xl shadow-lg z-50 overflow-hidden">
            {/* User Info Section */}
            <div className="p-4 border-b border-border-default">
              <div className="flex items-center gap-3">
                {avatarUrl ? (
                  <img
                    src={avatarUrl}
                    alt={fullName ?? 'User'}
                    className="w-10 h-10 rounded-full object-cover"
                  />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-accent-blue flex items-center justify-center text-background font-semibold">
                    {getInitials(fullName)}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-text-primary truncate">
                    {fullName || 'User'}
                  </p>
                  {email && (
                    <p className="text-xs text-text-secondary truncate">{email}</p>
                  )}
                </div>
              </div>
            </div>

            {/* Menu Items */}
            <div className="p-2">
              <button
                onClick={handleProfile}
                className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors text-left"
                aria-label="View profile"
              >
                <User className="w-4 h-4" />
                <span>Profile</span>
              </button>

              <div className="h-px bg-border-default my-1" />

              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-red-500 hover:bg-red-500/10 hover:text-red-600 transition-colors text-left"
                aria-label="Sign out"
              >
                <LogOut className="w-4 h-4" />
                <span>Sign out</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Draft Save Modal */}
      {draftInfo && (
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
