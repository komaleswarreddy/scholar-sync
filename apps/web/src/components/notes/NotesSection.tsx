'use client';

import { useState, useEffect } from 'react';
import { Plus } from 'lucide-react';
import { Button } from '../ui/Button';
import { NoteItem } from './NoteItem';
import { apiClient } from '@/lib/api-client';

interface Note {
  id: string;
  content: string;
  source_ref_id?: string;
  created_at?: string;
}

interface NoteWithExtras extends Note {
  title?: string;
  sourceCount?: number;
  isNew?: boolean;
  createdAt?: string;
}

export function NotesSection() {
  const [notes, setNotes] = useState<NoteWithExtras[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load notes on mount
  useEffect(() => {
    loadNotes();
  }, []);

  const loadNotes = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.listNotes(); // uses dev-user-123
      const transformedNotes = result.map((note: Note) => ({
        ...note,
        title:
          note.content?.substring(0, 50) +
          (note.content && note.content.length > 50 ? '...' : '') ||
          'New Note',
        sourceCount: 0,
        isNew: false,
        createdAt: note.created_at,
      }));
      setNotes(transformedNotes);
    } catch (err: any) {
      setError(err.message || 'Failed to load notes');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateNote = async () => {
    const content = prompt('Enter note content:');
    if (!content) return;

    setLoading(true);
    setError(null);
    try {
      await apiClient.createNote(content); // dev-user-123
      await loadNotes();
    } catch (err: any) {
      setError(err.message || 'Failed to create note');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteNote = async (id: string) => {
    if (!confirm('Delete this note?')) return;

    setLoading(true);
    setError(null);
    try {
      await apiClient.deleteNote(id); // dev-user-123
      await loadNotes();
    } catch (err: any) {
      setError(err.message || 'Failed to delete note');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-border-default flex items-center justify-between">
        <h2 className="text-lg font-medium text-text-primary">Notes</h2>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCreateNote}
          className="p-2 rounded-full"
          title="Create new note"
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
        ) : notes.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-text-secondary text-sm mb-2">No notes yet</p>
            <p className="text-text-tertiary text-xs">
              Create a note to save important information
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {notes.map((note) => (
              <NoteItem
                key={note.id}
                id={note.id}
                title={note.title || 'Untitled Note'}
                content={note.content || ''}
                sourceCount={note.sourceCount || 0}
                createdAt={note.createdAt || new Date().toISOString()}
                isNew={note.isNew || false}
                onDelete={handleDeleteNote}
              />
            ))}
          </div>
        )}
        {error && (
          <div className="mt-2 p-2 rounded-lg bg-red-500/10 border border-red-500/20">
            <p className="text-xs text-red-400">{error}</p>
          </div>
        )}
      </div>
    </div>
  );
}
