'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { Plus, Search, X } from 'lucide-react';
import { Button } from '../ui/Button';
import { NoteItem } from './NoteItem';
import { NoteEditor } from './NoteEditor';
import { apiClient } from '@/lib/api-client';
import { Input } from '../ui/Input';

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

type ViewMode = 'list' | 'create' | 'edit';

export function NotesSection() {
  const [notes, setNotes] = useState<NoteWithExtras[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const loadNotes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiClient.listNotes();
      const transformedNotes = result.map((note: Note) => {
        // Ensure we have a valid created_at date
        // Backend should always return created_at, but handle null/undefined cases
        const createdAt = note.created_at || note.updated_at || new Date().toISOString();
        
        // Debug logging to check what we're receiving
        if (!note.created_at && !note.updated_at) {
          console.warn('[NotesSection] Note missing created_at and updated_at:', note.id);
        }
        
        return {
          ...note,
          title:
            note.content?.substring(0, 50) +
            (note.content && note.content.length > 50 ? '...' : '') ||
            'New Note',
          sourceCount: note.source_ref_id ? 1 : 0,
          isNew: false,
          createdAt: createdAt,
        };
      });
      setNotes(transformedNotes);
    } catch (err: any) {
      let errorMessage = 'Failed to load notes';
      
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        errorMessage = 'Request timed out. Please check if the backend server is running.';
      } else if (err.code === 'ECONNREFUSED' || err.message?.includes('Failed to fetch')) {
        errorMessage = 'Cannot connect to server. Please check if the backend is running.';
      } else if (err.response?.status === 401) {
        errorMessage = 'Authentication required. Please sign in.';
      } else if (err.response?.status === 403) {
        errorMessage = 'Access denied. Please check your permissions.';
      } else {
        errorMessage = err.response?.data?.detail || err.message || 'Failed to load notes';
      }
      
      setError(errorMessage);
      console.error('Error loading notes:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load notes on mount
  useEffect(() => {
    loadNotes();
  }, [loadNotes]);

  // Listen for note creation events from other components (e.g., ChatMessage)
  useEffect(() => {
    const handleNoteCreated = () => {
      loadNotes();
    };

    window.addEventListener('noteCreated', handleNoteCreated);
    return () => {
      window.removeEventListener('noteCreated', handleNoteCreated);
    };
  }, [loadNotes]);

  const handleCreateNote = () => {
    setViewMode('create');
    setEditingNoteId(null);
  };

  const handleSaveNote = async (content: string, sourceRefId?: string) => {
    setLoading(true);
    setError(null);
    try {
      if (editingNoteId) {
        // Update existing note
        await apiClient.updateNote(editingNoteId, content);
      } else {
        // Create new note
        await apiClient.createNote(content, sourceRefId);
      }
      await loadNotes();
      setViewMode('list');
      setEditingNoteId(null);
    } catch (err: any) {
      let errorMessage = editingNoteId ? 'Failed to update note' : 'Failed to create note';
      
      if (err.response?.status === 400) {
        errorMessage = 'Invalid note content. Please check your input.';
      } else if (err.response?.status === 404) {
        errorMessage = 'Note not found. It may have been deleted.';
      } else if (err.response?.status === 500) {
        errorMessage = 'Server error. Please try again later.';
      } else {
        errorMessage = err.response?.data?.detail || err.message || errorMessage;
      }
      
      setError(errorMessage);
      console.error('Error saving note:', err);
      throw err; // Re-throw to let NoteEditor handle it
    } finally {
      setLoading(false);
    }
  };

  const handleCancelEdit = () => {
    setViewMode('list');
    setEditingNoteId(null);
  };

  const handleEditNote = (id: string) => {
    setEditingNoteId(id);
    setViewMode('edit');
  };

  const handleDeleteNote = async (id: string) => {
    // Better confirmation dialog
    const confirmed = window.confirm('Are you sure you want to delete this note? This action cannot be undone.');
    if (!confirmed) return;

    setLoading(true);
    setError(null);
    try {
      await apiClient.deleteNote(id);
      await loadNotes();
    } catch (err: any) {
      let errorMessage = 'Failed to delete note';
      
      if (err.response?.status === 404) {
        errorMessage = 'Note not found. It may have already been deleted.';
      } else if (err.response?.status === 403) {
        errorMessage = 'You do not have permission to delete this note.';
      } else {
        errorMessage = err.response?.data?.detail || err.message || errorMessage;
      }
      
      setError(errorMessage);
      console.error('Error deleting note:', err);
    } finally {
      setLoading(false);
    }
  };

  // Filter notes based on search query
  const filteredNotes = useMemo(() => {
    if (!searchQuery.trim()) {
      return notes;
    }
    const query = searchQuery.toLowerCase();
    return notes.filter(
      (note) =>
        note.content?.toLowerCase().includes(query) ||
        note.title?.toLowerCase().includes(query)
    );
  }, [notes, searchQuery]);

  // Get note being edited
  const editingNote = useMemo(() => {
    if (!editingNoteId) return null;
    return notes.find((n) => n.id === editingNoteId);
  }, [notes, editingNoteId]);

  // Show editor if in create or edit mode
  if (viewMode === 'create' || viewMode === 'edit') {
    return (
      <div className="flex flex-col h-full">
        <div className="p-4 border-b border-border-default flex items-center justify-between">
          <h2 className="text-lg font-medium text-text-primary">
            {viewMode === 'create' ? 'New Note' : 'Edit Note'}
          </h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCancelEdit}
            className="p-2 rounded-full"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
        <div className="flex-1 overflow-hidden">
          <NoteEditor
            initialContent={editingNote?.content || ''}
            onSave={handleSaveNote}
            onCancel={handleCancelEdit}
            noteId={editingNoteId || undefined}
          />
        </div>
        {error && (
          <div className="p-4 border-t border-border-default">
            <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/20">
              <p className="text-xs text-red-400">{error}</p>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Show list view
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
          disabled={loading}
        >
          <Plus className="w-4 h-4" />
        </Button>
      </div>

      {/* Search Bar */}
      {notes.length > 0 && (
        <div className="p-4 border-b border-border-default">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-text-tertiary" />
            <Input
              type="text"
              placeholder="Search notes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 pr-4 py-2 w-full"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-text-tertiary hover:text-text-primary"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Notes List */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading && notes.length === 0 ? (
          <div className="text-center py-8">
            <div className="w-6 h-6 border-2 border-accent-blue border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-text-secondary text-sm">Loading notes...</p>
          </div>
        ) : filteredNotes.length === 0 && !loading ? (
          <div className="text-center py-8">
            {searchQuery ? (
              <>
                <p className="text-text-secondary text-sm mb-2">No notes found</p>
                <p className="text-text-tertiary text-xs">
                  Try adjusting your search query
                </p>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSearchQuery('')}
                  className="mt-4"
                >
                  Clear search
                </Button>
              </>
            ) : (
              <>
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
              </>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            {filteredNotes.map((note) => (
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
              onClick={() => setError(null)}
              className="mt-1 text-xs text-red-400 hover:text-red-300 underline"
            >
              Dismiss
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
