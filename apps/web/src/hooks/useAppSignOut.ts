'use client';

import { useCallback, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { apiClient } from '@/lib/api-client';
import { checkForNoteDrafts, removeDraft } from '@/lib/note-draft-utils';

export function useAppSignOut() {
  const { signOut } = useAuth();
  const [showDraftModal, setShowDraftModal] = useState(false);
  const [draftInfo, setDraftInfo] = useState<{
    draftKey: string;
    draftContent: string;
  } | null>(null);

  const completeSignOut = useCallback(async () => {
    await signOut();
  }, [signOut]);

  const signOutWithDraftCheck = useCallback(async () => {
    const { hasDraft, draftKey, draftContent } = checkForNoteDrafts();

    if (hasDraft && draftContent && draftKey) {
      setDraftInfo({ draftKey, draftContent });
      setShowDraftModal(true);
      return;
    }

    apiClient.clearAuthSession();
    await completeSignOut();
  }, [completeSignOut]);

  const handleDraftSave = useCallback(() => {
    if (draftInfo) {
      removeDraft(draftInfo.draftKey);
    }
    setShowDraftModal(false);
    setDraftInfo(null);
    apiClient.clearAuthSession();
    void completeSignOut();
  }, [draftInfo, completeSignOut]);

  const handleDraftDiscard = useCallback(() => {
    if (draftInfo) {
      removeDraft(draftInfo.draftKey);
    }
    setShowDraftModal(false);
    setDraftInfo(null);
    apiClient.clearAuthSession();
    void completeSignOut();
  }, [draftInfo, completeSignOut]);

  const handleDraftCancel = useCallback(() => {
    setShowDraftModal(false);
    setDraftInfo(null);
  }, []);

  return {
    signOutWithDraftCheck,
    showDraftModal,
    draftInfo,
    handleDraftSave,
    handleDraftDiscard,
    handleDraftCancel,
  };
}
