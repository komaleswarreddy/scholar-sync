'use client';

import { LogOut } from 'lucide-react';
import { useAppSignOut } from '@/hooks/useAppSignOut';
import { useUserContext } from '@/contexts/UserContext';
import { emptyProfileLabel } from '@/lib/profile-utils';
import { DraftSaveModal } from '@/components/notes/DraftSaveModal';
import { ProfileField } from '../ProfileField';
import { ProfileFormFooter } from '../ProfileFormFooter';
import { ProfileSummaryHeader } from '../ProfileSummaryHeader';

export function AccountSecuritySection() {
  const { user } = useUserContext();
  const {
    signOutWithDraftCheck,
    showDraftModal,
    draftInfo,
    handleDraftSave,
    handleDraftDiscard,
    handleDraftCancel,
  } = useAppSignOut();

  const loginId = user?.email || user?.username || '—';

  return (
    <div className="profile-main-card">
      <ProfileSummaryHeader />

      <h3 className="text-[16px] font-bold text-[var(--color-home-text)] mt-8 mb-4">
        Login & Security
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <ProfileField label="Username" value={emptyProfileLabel(user?.username)} readOnly />
        <ProfileField label="Login email" value={emptyProfileLabel(user?.email, '—')} readOnly />
        <ProfileField label="Sign-in ID" value={loginId} colSpan={2} readOnly />
        <ProfileField label="Password" value="••••••••••" readOnly />
        <ProfileField label="Role" value={emptyProfileLabel(user?.role)} readOnly />
      </div>

      <div className="flex flex-wrap gap-3 mt-4">
        <button type="button" className="profile-btn-secondary text-[13px] py-2 px-4" disabled>
          Change password
        </button>
        <p className="text-[12px] text-[var(--color-home-text-muted)] self-center">
          Password changes are managed by your school admin.
        </p>
      </div>

      <div className="profile-sign-out-panel mt-8">
        <h3 className="text-[16px] font-bold text-[var(--color-home-text)] mb-2">Session</h3>
        <p className="text-[14px] text-[var(--color-home-text-muted)] mb-4 leading-relaxed">
          Sign out of ScholarSync on this device. Unsaved note drafts will be offered to save first.
        </p>
        <button
          type="button"
          className="profile-sign-out-btn"
          onClick={() => void signOutWithDraftCheck()}
        >
          <LogOut className="w-4 h-4" strokeWidth={1.75} />
          Sign out
        </button>
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

      <ProfileFormFooter />
    </div>
  );
}
