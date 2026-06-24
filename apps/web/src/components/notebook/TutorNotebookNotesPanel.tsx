'use client';

import { FileText } from 'lucide-react';
import { NotesListSkeleton } from '@/components/skeleton';
import { useNotebookScopeId } from '@/contexts/NotebookContext';
import { useNotes, useUpdateNote } from '@/hooks/useNotes';
import { notePreviewTitle } from '@/lib/note-content';
import { formatRelativeTime } from '@/lib/notebook-ui-tokens';
import type { TutorActiveNote } from '@/contexts/TutorNoteEditorContext';
import {
  NoteCreateOrAppendMenu,
  buildAppendedNoteContent,
} from '@/components/notes/NoteCreateOrAppendMenu';
import { useAppToast } from '@/contexts/AppToastContext';

const PREVIEW_LIMIT = 5;

interface TutorNotebookNotesPanelProps {
  onOpenNote: (note: TutorActiveNote) => void;
}

export function TutorNotebookNotesPanel({ onOpenNote }: TutorNotebookNotesPanelProps) {
  const notebookId = useNotebookScopeId();
  const { data: notes = [], isLoading } = useNotes(notebookId);
  const updateNote = useUpdateNote();
  const { showToast } = useAppToast();
  const previewNotes = notes.slice(0, PREVIEW_LIMIT);

  const handleAppendToNote = async (noteId: string, content: string) => {
    const existing = notes.find((note) => note.id === noteId);
    if (!existing) return;
    const nextContent = await buildAppendedNoteContent(existing.content, content);
    await updateNote.mutateAsync({ noteId, content: nextContent });
    showToast(`Added to ${notePreviewTitle(existing.content)}`);
    onOpenNote(noteId);
  };

  return (
    <div className="flex flex-col min-h-0">
      <div className="notebook-col-header px-4 pt-3 pb-1">
        <span>NOTES</span>
        <NoteCreateOrAppendMenu
          notes={notes}
          triggerLabel="+ New note"
          appendContent=""
          onCreateNew={() => onOpenNote('new')}
          onAppendToNote={handleAppendToNote}
        />
      </div>

      {isLoading && notes.length === 0 ? (
        <div className="px-4 pb-2">
          <NotesListSkeleton count={2} />
        </div>
      ) : previewNotes.length === 0 ? (
        <p className="text-[12px] text-[var(--color-home-text-muted)] px-4 py-2">
          No notes yet. Create one to capture ideas from this chapter.
        </p>
      ) : (
        <ul className="notebook-notes-list notebook-notes-list--scroll px-4 pb-2 max-h-40 overflow-y-auto">
          {previewNotes.map((note) => (
            <li key={note.id}>
              <button
                type="button"
                className="notebook-note-row w-full text-left"
                onClick={() => onOpenNote(note.id)}
              >
                <FileText className="w-4 h-4 text-[var(--color-brand-text)] flex-shrink-0" />
                <span className="flex-1 text-[13px] font-medium text-[var(--color-home-text)] truncate">
                  {notePreviewTitle(note.content)}
                </span>
                <span className="text-[11px] text-[var(--color-home-label)] flex-shrink-0">
                  {formatRelativeTime(note.updated_at || note.created_at)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      {notes.length > PREVIEW_LIMIT && (
        <p className="px-4 pb-3 text-[11px] text-[var(--color-home-text-muted)]">
          {notes.length - PREVIEW_LIMIT} more note{notes.length - PREVIEW_LIMIT === 1 ? '' : 's'}
        </p>
      )}
    </div>
  );
}
