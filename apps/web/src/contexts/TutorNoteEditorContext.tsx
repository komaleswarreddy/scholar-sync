'use client';

import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';

export type TutorActiveNote = 'new' | string | null;

interface TutorNoteEditorContextValue {
  activeNote: TutorActiveNote;
  setActiveNote: (note: TutorActiveNote) => void;
  isEditorOpen: boolean;
}

const TutorNoteEditorContext = createContext<TutorNoteEditorContextValue | null>(null);

export function TutorNoteEditorProvider({ children }: { children: ReactNode }) {
  const [activeNote, setActiveNote] = useState<TutorActiveNote>(null);
  const value = useMemo(
    () => ({
      activeNote,
      setActiveNote,
      isEditorOpen: activeNote !== null,
    }),
    [activeNote],
  );

  return (
    <TutorNoteEditorContext.Provider value={value}>{children}</TutorNoteEditorContext.Provider>
  );
}

export function useTutorNoteEditor() {
  const ctx = useContext(TutorNoteEditorContext);
  if (!ctx) {
    throw new Error('useTutorNoteEditor must be used within TutorNoteEditorProvider');
  }
  return ctx;
}

export function useOptionalTutorNoteEditor() {
  return useContext(TutorNoteEditorContext);
}
