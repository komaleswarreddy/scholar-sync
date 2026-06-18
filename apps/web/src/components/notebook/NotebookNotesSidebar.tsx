'use client';

import { useEffect, useState } from 'react';
import { ChevronRight, FileText, Loader2 } from 'lucide-react';
import { useNotebookContext, useNotebookScopeId } from '@/contexts/NotebookContext';
import { useNotes, useCreateNote, useUpdateNote, noteKeys } from '@/hooks/useNotes';
import { useQueryClient } from '@tanstack/react-query';
import { formatNoteTitle, formatRelativeTime } from '@/lib/notebook-ui-tokens';
import { NoteModal } from '@/components/notes/NoteModal';
import { NotesViewAllDialog } from './NotesViewAllDialog';

const PREVIEW_LIMIT = 5;

export function NotebookNotesSidebar() {
  const notebookId = useNotebookScopeId();
  const { notebook } = useNotebookContext();
  const { data: notes = [], isLoading } = useNotes(notebookId);
  const createMutation = useCreateNote(notebookId);
  const updateMutation = useUpdateNote();
  const queryClient = useQueryClient();

  const [viewAllOpen, setViewAllOpen] = useState(false);
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    const handleNoteCreated = () => {
      queryClient.invalidateQueries({ queryKey: noteKeys.list(notebookId) });
    };
    window.addEventListener('noteCreated', handleNoteCreated);
    return () => window.removeEventListener('noteCreated', handleNoteCreated);
  }, [queryClient, notebookId]);

  const previewNotes = notes.slice(0, PREVIEW_LIMIT);
  const editingNote = editingNoteId ? notes.find((n) => n.id === editingNoteId) : null;
  const modalOpen = isCreating || !!editingNote;

  const handleSaveNote = async (content: string, sourceRefId?: string) => {
    if (editingNoteId) {
      await updateMutation.mutateAsync({ noteId: editingNoteId, content });
    } else {
      await createMutation.mutateAsync({ content, sourceRefId });
    }
    setIsCreating(false);
    setEditingNoteId(null);
  };

  const closeModal = () => {
    setIsCreating(false);
    setEditingNoteId(null);
  };

  return (
    <>
      <div className="notebook-col-section notebook-col-section--notes flex flex-col min-h-0 h-full">
        <div className="notebook-col-header">
          <span>NOTEBOOK NOTES</span>
          <button
            type="button"
            className="notebook-link-btn"
            onClick={() => {
              setIsCreating(true);
              setEditingNoteId(null);
            }}
          >
            + New note
          </button>
        </div>

        {isLoading && notes.length === 0 ? (
          <div className="flex items-center justify-center py-6 text-[var(--color-home-text-muted)]">
            <Loader2 className="w-4 h-4 animate-spin mr-2" />
            <span className="text-[12px]">Loading notes…</span>
          </div>
        ) : previewNotes.length === 0 ? (
          <p className="text-[12px] text-[var(--color-home-text-muted)] px-1 py-2">
            No notes yet. Create one to capture ideas from this notebook.
          </p>
        ) : (
          <ul className="notebook-notes-list notebook-notes-list--scroll flex-1 min-h-0 overflow-y-auto">
            {previewNotes.map((note) => (
              <li key={note.id}>
                <button
                  type="button"
                  className="notebook-note-row w-full text-left"
                  onClick={() => {
                    setEditingNoteId(note.id);
                    setIsCreating(false);
                  }}
                >
                  <FileText className="w-4 h-4 text-[var(--color-brand-text)] flex-shrink-0" />
                  <span className="flex-1 text-[13px] font-medium text-[var(--color-home-text)] truncate">
                    {formatNoteTitle(note.content)}
                  </span>
                  <span className="text-[11px] text-[var(--color-home-label)] flex-shrink-0">
                    {formatRelativeTime(note.updated_at || note.created_at)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}

        <button type="button" onClick={() => setViewAllOpen(true)} className="notebook-view-all-btn">
          View all notes
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      <NotesViewAllDialog
        open={viewAllOpen}
        notes={notes}
        notebookTitle={notebook.title}
        onClose={() => setViewAllOpen(false)}
        onEditNote={(id) => {
          setViewAllOpen(false);
          setEditingNoteId(id);
          setIsCreating(false);
        }}
      />

      {modalOpen && (
        <NoteModal
          isOpen={modalOpen}
          onClose={closeModal}
          noteId={editingNoteId}
          initialContent={editingNote?.content || ''}
          title={editingNote ? formatNoteTitle(editingNote.content) : 'New note'}
          isSaving={createMutation.isPending || updateMutation.isPending}
          onSave={handleSaveNote}
        />
      )}
    </>
  );
}
