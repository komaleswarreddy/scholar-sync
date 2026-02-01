'use client';

import { useState, useEffect, useMemo } from 'react';
import { Plus } from 'lucide-react';
import { Button } from '../ui/Button';
import { NoteItem } from './NoteItem';
import { NoteModal } from './NoteModal';
import { useNotes, useCreateNote, useUpdateNote, useDeleteNote } from '@/hooks/useNotes';
import { useQueryClient } from '@tanstack/react-query';
import { noteKeys } from '@/hooks/useNotes';

interface Note {
  id: string;
  content: string;
  source_ref_id?: string;
  created_at?: string;
  updated_at?: string;
}

interface NoteWithExtras extends Note {
  title?: string;
  sourceCount?: number;
  isNew?: boolean;
  createdAt?: string;
}

export function NotesSection() {
  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);
  const [isCreatingNote, setIsCreatingNote] = useState(false);

  // Task C.a & C.b: Use TanStack Query for notes with loading states and caching
  const { data: notes = [], isLoading: loading, error: queryError } = useNotes();
  const createMutation = useCreateNote();
  const updateMutation = useUpdateNote();
  const deleteMutation = useDeleteNote();
  const queryClient = useQueryClient();

  // Task C.a: Loading state from TanStack Query
  // Ensure error is always a string, not an Error object
  const error = queryError 
    ? (typeof queryError === 'string' 
        ? queryError 
        : queryError?.message || queryError?.toString() || 'An error occurred')
    : null;

  // Listen for note creation events from other components (e.g., ChatMessage)
  useEffect(() => {
    const handleNoteCreated = () => {
      // Invalidate notes query to refetch
      queryClient.invalidateQueries({ queryKey: noteKeys.list() });
    };

    window.addEventListener('noteCreated', handleNoteCreated);
    return () => {
      window.removeEventListener('noteCreated', handleNoteCreated);
    };
  }, [queryClient]);

  const handleCreateNote = () => {
    setIsCreatingNote(true);
    setSelectedNoteId(null);
  };

  const handleSaveNote = async (content: string, sourceRefId?: string) => {
    try {
      if (selectedNoteId) {
        // Task C.c: Optimistic update handled by TanStack Query
        await updateMutation.mutateAsync({ noteId: selectedNoteId, content });
      } else {
        await createMutation.mutateAsync({ content, sourceRefId });
      }
      setIsCreatingNote(false);
      setSelectedNoteId(null);
    } catch (err: any) {
      // Error is handled by TanStack Query, but re-throw for NoteModal
      throw err;
    }
  };

  const handleEditNote = (id: string) => {
    setSelectedNoteId(id);
    setIsCreatingNote(false);
  };

  const handleCloseModal = () => {
    setIsCreatingNote(false);
    setSelectedNoteId(null);
  };

  const handleDeleteNote = async (id: string) => {
    // Better confirmation dialog
    const confirmed = window.confirm('Are you sure you want to delete this note? This action cannot be undone.');
    if (!confirmed) return;

    try {
      // Task C.c: Optimistic update handled by TanStack Query
      await deleteMutation.mutateAsync(id);
    } catch (err: any) {
      // Error is handled by TanStack Query
      console.error('Error deleting note:', err);
    }
  };


  // Get selected note
  const selectedNote = useMemo(() => {
    if (!selectedNoteId) return null;
    return notes.find((n) => n.id === selectedNoteId);
  }, [notes, selectedNoteId]);

  // Show list view
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="h-14 flex items-center px-4 border-b border-border-default justify-between">
        <h2 className="text-lg font-medium text-text-primary">Notes</h2>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCreateNote}
          className="p-2 rounded-full"
          title="Create new note"
          disabled={loading}
        >
          <Plus className="w-4 h-4" />
        </Button>
      </div>

      {/* Notes List */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading && notes.length === 0 ? (
          <div className="text-center py-8">
            <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-text-secondary text-sm">Loading notes...</p>
          </div>
        ) : notes.length === 0 && !loading ? (
          <div className="text-center py-8">
            <p className="text-text-secondary text-sm mb-2">No notes yet</p>
            <p className="text-text-tertiary text-xs mb-4">
              Create a note to save important information
            </p>
            <Button
              variant="primary"
              size="sm"
              onClick={handleCreateNote}
              className="bg-accent-blue text-background"
            >
              <Plus className="w-4 h-4 mr-1" />
              Create your first note
            </Button>
          </div>
        ) : (
          <div className="space-y-2">
            {notes.map((note) => (
              <NoteItem
                key={note.id}
                id={note.id}
                title={note.title || 'Untitled Note'}
                content={note.content || ''}
                sourceRefId={note.source_ref_id}
                sourceCount={note.sourceCount || 0}
                createdAt={note.createdAt || note.created_at || note.updated_at || new Date().toISOString()}
                isNew={note.isNew || false}
                onDelete={handleDeleteNote}
                onEdit={handleEditNote}
              />
            ))}
          </div>
        )}
        {error && (
          <div className="mt-2 p-2 rounded-lg bg-red-500/10 border border-red-500/20">
            <p className="text-xs text-red-400">{error}</p>
            <button
              onClick={() => {
                // Invalidate query to clear error
                queryClient.invalidateQueries({ queryKey: noteKeys.list() });
              }}
              className="mt-1 text-xs text-red-400 hover:text-red-300 underline"
            >
              Dismiss
            </button>
          </div>
        )}
      </div>

      {/* Note Modal */}
      {(isCreatingNote || selectedNote) && (
        <NoteModal
          isOpen={isCreatingNote || !!selectedNote}
          onClose={handleCloseModal}
          noteId={selectedNoteId}
          initialContent={selectedNote?.content || ''}
          onSave={handleSaveNote}
          title={selectedNote ? (selectedNote.title || 'Note') : 'New Note'}
          isSaving={createMutation.isPending || updateMutation.isPending}
          error={error}
        />
      )}
    </div>
  );
}
