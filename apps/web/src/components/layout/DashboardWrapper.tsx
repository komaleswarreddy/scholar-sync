'use client';

import { useEffect, useState, useRef } from 'react';
import { Header } from '@/components/layout/Header';
import { SourceList } from '@/components/sources/SourceList';
import { StudioSuite } from '@/components/studio/StudioSuite';
import { NotesSection } from '@/components/notes/NotesSection';
import { SourceProvider } from '@/contexts/SourceContext';
import { UserProvider, useUserContext } from '@/contexts/UserContext';
import { checkForNoteDrafts, removeDraft } from '@/lib/note-draft-utils';
import { DraftSaveModal } from '@/components/notes/DraftSaveModal';

export function DashboardWrapper({ children }: { children: React.ReactNode }) {
  const Wrapper = () => {
    const { isSignedIn, loading } = useUserContext();
    const [draftInfo, setDraftInfo] = useState<{
      draftKey: string;
      draftContent: string;
    } | null>(null);
    const [showDraftModal, setShowDraftModal] = useState(false);
    const pendingNavigationRef = useRef<(() => void) | null>(null);
    const isShowingModalRef = useRef(false);
    const draftInfoRef = useRef<{ draftKey: string; draftContent: string } | null>(null);

    // Intercept refresh attempts to show modal
    useEffect(() => {
      if (typeof window === 'undefined') return;

      const handleKeyDown = (e: KeyboardEvent) => {
        // Check for refresh shortcuts
        const isRefresh = 
          (e.key === 'F5') ||
          ((e.ctrlKey || e.metaKey) && e.key === 'r') ||
          ((e.ctrlKey || e.metaKey) && e.key === 'R');

        if (isRefresh) {
          const { hasDraft, draftKey, draftContent } = checkForNoteDrafts();
          if (hasDraft && draftKey && draftContent) {
            e.preventDefault();
            e.stopPropagation();
            setDraftInfo({ draftKey, draftContent });
            setShowDraftModal(true);
            // Store navigation action - will be executed after user decides
            pendingNavigationRef.current = () => {
              // User chose to save or discard - allow refresh
              window.location.reload();
            };
          }
        }
      };

      // Handle beforeunload for browser refresh button - show our modal
      // Note: If user has blocked dialogs, this may not work for browser refresh button
      // Keyboard shortcuts (F5, Ctrl+R) will still work as they're intercepted earlier
      const handleBeforeUnload = (e: BeforeUnloadEvent) => {
        // CRITICAL: Always prevent navigation if modal is showing
        // This ensures the page doesn't reload while user is interacting with modal
        if (isShowingModalRef.current || showDraftModal) {
          e.preventDefault();
          e.returnValue = '';
          return '';
        }
        
        const { hasDraft, draftKey, draftContent } = checkForNoteDrafts();
        if (hasDraft && draftKey && draftContent) {
          // Try to prevent navigation (may not work if dialogs are blocked)
          try {
            e.preventDefault();
            e.returnValue = '';
            
            // Mark that we're showing modal immediately (synchronously)
            isShowingModalRef.current = true;
            
            // Store draft info in ref for immediate access
            draftInfoRef.current = { draftKey, draftContent };
            
            // Set state - React will render modal
            setDraftInfo({ draftKey, draftContent });
            setShowDraftModal(true);
            
            pendingNavigationRef.current = () => {
              // Only reload after user explicitly chooses Save or Discard
              isShowingModalRef.current = false;
              draftInfoRef.current = null;
              setTimeout(() => {
                window.location.reload();
              }, 100);
            };
            
            // Return empty string to prevent navigation
            return '';
          } catch (error) {
            // If beforeunload is blocked, at least try to show modal
            // (though navigation may proceed)
            console.warn('beforeunload handler blocked by browser');
          }
        }
      };

      window.addEventListener('keydown', handleKeyDown, true); // Use capture phase
      window.addEventListener('beforeunload', handleBeforeUnload);
      
      // Also listen for visibility change to catch if page is trying to unload
      const handleVisibilityChange = () => {
        if (document.hidden && isShowingModalRef.current) {
          // Page is trying to unload but modal is showing - prevent it
          // This is a fallback to prevent navigation
        }
      };
      
      document.addEventListener('visibilitychange', handleVisibilityChange);
      
      return () => {
        window.removeEventListener('keydown', handleKeyDown, true);
        window.removeEventListener('beforeunload', handleBeforeUnload);
        document.removeEventListener('visibilitychange', handleVisibilityChange);
      };
    }, [showDraftModal]);


    const handleDraftSave = () => {
      // Draft was saved as note, remove it from localStorage
      if (draftInfo) {
        removeDraft(draftInfo.draftKey);
      }
      isShowingModalRef.current = false;
      setShowDraftModal(false);
      setDraftInfo(null);
      // Allow navigation to proceed if pending
      if (pendingNavigationRef.current) {
        pendingNavigationRef.current();
        pendingNavigationRef.current = null;
      }
    };

    const handleDraftDiscard = () => {
      // User chose to discard - remove draft
      if (draftInfo) {
        removeDraft(draftInfo.draftKey);
      }
      isShowingModalRef.current = false;
      setShowDraftModal(false);
      setDraftInfo(null);
      // Allow navigation to proceed if pending
      if (pendingNavigationRef.current) {
        pendingNavigationRef.current();
        pendingNavigationRef.current = null;
      }
    };

    const handleDraftCancel = () => {
      // User cancelled - don't navigate, just close modal
      isShowingModalRef.current = false;
      draftInfoRef.current = null;
      setShowDraftModal(false);
      setDraftInfo(null);
      pendingNavigationRef.current = null;
    };

    if (loading) return <p>Loading...</p>;
    if (!isSignedIn) return <p>Redirecting to login...</p>;

    return (
      <div className="h-screen w-screen flex flex-col overflow-hidden bg-background">
        <Header />
        <div className="flex-1 flex gap-4 p-4 overflow-hidden">
          <aside className="w-[18%] bg-surface rounded-3xl flex flex-col overflow-hidden border border-border-default">
            <SourceList />
          </aside>
          <main className="flex-1 flex flex-col bg-surface rounded-3xl overflow-hidden border border-border-default min-w-0">
            {children}
          </main>
          <aside className="w-[18%] bg-surface rounded-3xl flex flex-col overflow-hidden border border-border-default">
            <div className="flex-1 border-b border-border-default min-h-0">
              <StudioSuite />
            </div>
            <div className="flex-1 min-h-0">
              <NotesSection />
            </div>
          </aside>
        </div>

        {/* Draft Save Modal - shown on refresh/logout attempts */}
        {draftInfo && (
          <DraftSaveModal
            isOpen={showDraftModal}
            draftContent={draftInfo.draftContent}
            onSave={handleDraftSave}
            onDiscard={handleDraftDiscard}
            onCancel={handleDraftCancel}
          />
        )}
      </div>
    );
  };

  return (
    <UserProvider>
      <SourceProvider>
        <Wrapper />
      </SourceProvider>
    </UserProvider>
  );
}
