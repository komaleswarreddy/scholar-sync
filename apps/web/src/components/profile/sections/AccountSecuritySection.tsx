'use client';

import { LogOut } from 'lucide-react';
import { PROFILE_ACCOUNT } from '@/lib/profile-mock-data';
import { useAppSignOut } from '@/hooks/useAppSignOut';
import { DraftSaveModal } from '@/components/notes/DraftSaveModal';
import { ProfileField } from '../ProfileField';
import { ProfileFormFooter } from '../ProfileFormFooter';
import { ProfileSummaryHeader } from '../ProfileSummaryHeader';

export function AccountSecuritySection() {
  const d = PROFILE_ACCOUNT;
  const {
    signOutWithDraftCheck,
    showDraftModal,
    draftInfo,
    handleDraftSave,
    handleDraftDiscard,
    handleDraftCancel,
  } = useAppSignOut();

  return (
    <div className="profile-main-card">
      <ProfileSummaryHeader />

      <h3 className="text-[16px] font-bold text-[var(--color-home-text)] mt-8 mb-4">
        Login & Security
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <ProfileField label="Login email" value={d.loginEmail} colSpan={2} />
        <ProfileField label="Password" value="••••••••••" />
        <ProfileField label="Last changed" value={d.lastPasswordChange} />
        <ProfileField label="Devices" value={d.devices} colSpan={2} />
        <ProfileField label="Data controls" value={d.dataControls} colSpan={2} />
      </div>

      <div className="flex flex-wrap gap-3 mt-4">
        <button type="button" className="profile-btn-secondary text-[13px] py-2 px-4">
          Change password
        </button>
        <button type="button" className="profile-btn-secondary text-[13px] py-2 px-4">
          Manage devices
        </button>
        <button type="button" className="profile-btn-secondary text-[13px] py-2 px-4 text-[#DC2626] border-[#FECACA] hover:bg-[#FEF2F2]">
          Export my data
        </button>
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
