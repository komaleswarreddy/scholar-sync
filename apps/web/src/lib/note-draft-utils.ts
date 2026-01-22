/**
 * Utility functions for managing note drafts in localStorage
 */

/**
 * Check if there are any unsaved note drafts in localStorage
 * @returns Object with hasDraft flag and draft info
 */
export function checkForNoteDrafts(): {
  hasDraft: boolean;
  draftKey: string | null;
  draftContent: string | null;
} {
  if (typeof window === 'undefined') {
    return { hasDraft: false, draftKey: null, draftContent: null };
  }

  try {
    // Check for new note draft
    const newNoteDraft = localStorage.getItem('note-draft-new');
    if (newNoteDraft && newNoteDraft.trim()) {
      return {
        hasDraft: true,
        draftKey: 'note-draft-new',
        draftContent: newNoteDraft,
      };
    }

    // Check for existing note drafts (note-draft-*)
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith('note-draft-') && key !== 'note-draft-new') {
        const draft = localStorage.getItem(key);
        if (draft && draft.trim()) {
          return {
            hasDraft: true,
            draftKey: key,
            draftContent: draft,
          };
        }
      }
    }

    return { hasDraft: false, draftKey: null, draftContent: null };
  } catch (error) {
    console.error('[NoteDraftUtils] Error checking for drafts:', error);
    return { hasDraft: false, draftKey: null, draftContent: null };
  }
}

/**
 * Remove a specific draft from localStorage
 */
export function removeDraft(draftKey: string): void {
  if (typeof window === 'undefined') return;
  
  try {
    localStorage.removeItem(draftKey);
  } catch (error) {
    console.error(`[NoteDraftUtils] Error removing draft ${draftKey}:`, error);
  }
}

/**
 * Remove all note drafts from localStorage
 */
export function removeAllDrafts(): void {
  if (typeof window === 'undefined') return;
  
  try {
    // Remove new note draft
    localStorage.removeItem('note-draft-new');
    
    // Remove all note-draft-* items
    const keysToRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith('note-draft-')) {
        keysToRemove.push(key);
      }
    }
    
    keysToRemove.forEach(key => localStorage.removeItem(key));
  } catch (error) {
    console.error('[NoteDraftUtils] Error removing all drafts:', error);
  }
}
