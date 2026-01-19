/**
 * TanStack Query hooks for Notes API
 * 
 * Provides loading states, caching, and optimistic updates for note operations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { handleApiError, getUserFriendlyMessage } from '@/lib/error-handler';

// Query keys
export const noteKeys = {
  all: ['notes'] as const,
  lists: () => [...noteKeys.all, 'list'] as const,
  list: () => [...noteKeys.lists()] as const,
  details: () => [...noteKeys.all, 'detail'] as const,
  detail: (id: string) => [...noteKeys.details(), id] as const,
};

// Types
export interface Note {
  id: string;
  content: string;
  source_ref_id?: string;
  created_at: string;
  updated_at: string;
}

export interface NoteWithExtras extends Note {
  title: string;
  sourceCount: number;
  isNew: boolean;
  createdAt: string;
}

/**
 * Transform note to NoteWithExtras
 */
function transformNote(note: Note): NoteWithExtras {
  const createdAt = note.created_at || note.updated_at || new Date().toISOString();
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
}

/**
 * Hook to fetch all notes
 */
export function useNotes() {
  return useQuery({
    queryKey: noteKeys.list(),
    queryFn: async () => {
      try {
        const result = await apiClient.listNotes();
        const notes = (result || []) as Note[];
        return notes.map(transformNote);
      } catch (error: any) {
        const apiError = error.apiError || handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    staleTime: 60 * 1000, // 1 minute
  });
}

/**
 * Hook to fetch a single note
 */
export function useNote(noteId: string | null) {
  return useQuery({
    queryKey: noteKeys.detail(noteId || ''),
    queryFn: async () => {
      if (!noteId) return null;
      try {
        const result = await apiClient.getNote(noteId);
        return result as Note;
      } catch (error: any) {
        const apiError = error.apiError || handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    enabled: !!noteId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to create a note
 */
export function useCreateNote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      content,
      sourceRefId,
    }: {
      content: string;
      sourceRefId?: string;
    }) => {
      try {
        const result = await apiClient.createNote(content, sourceRefId);
        return result as Note;
      } catch (error: any) {
        const apiError = error.apiError || handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    onSuccess: (newNote) => {
      // Invalidate notes list to refetch
      queryClient.invalidateQueries({ queryKey: noteKeys.list() });
      // Optionally set the new note in cache
      if (newNote?.id) {
        queryClient.setQueryData(noteKeys.detail(newNote.id), newNote);
      }
    },
  });
}

/**
 * Hook to update a note
 */
export function useUpdateNote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      noteId,
      content,
    }: {
      noteId: string;
      content: string;
    }) => {
      try {
        const result = await apiClient.updateNote(noteId, content);
        return result as Note;
      } catch (error: any) {
        const apiError = error.apiError || handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    // Optimistic update: update note in cache immediately
    onMutate: async ({ noteId, content }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: noteKeys.list() });
      await queryClient.cancelQueries({ queryKey: noteKeys.detail(noteId) });

      // Snapshot the previous values
      const previousNotes = queryClient.getQueryData<NoteWithExtras[]>(noteKeys.list());
      const previousNote = queryClient.getQueryData<Note>(noteKeys.detail(noteId));

      // Optimistically update the note in the list
      queryClient.setQueryData<NoteWithExtras[]>(noteKeys.list(), (old) => {
        if (!old) return old;
        return old.map((note) =>
          note.id === noteId
            ? {
                ...note,
                content,
                updated_at: new Date().toISOString(),
                title:
                  content.substring(0, 50) + (content.length > 50 ? '...' : '') ||
                  'New Note',
              }
            : note
        );
      });

      // Optimistically update the single note
      if (previousNote) {
        queryClient.setQueryData<Note>(noteKeys.detail(noteId), {
          ...previousNote,
          content,
          updated_at: new Date().toISOString(),
        });
      }

      // Return context with snapshotted values
      return { previousNotes, previousNote };
    },
    // If the mutation fails, use the context to roll back
    onError: (err, variables, context) => {
      if (context?.previousNotes) {
        queryClient.setQueryData(noteKeys.list(), context.previousNotes);
      }
      if (context?.previousNote) {
        queryClient.setQueryData(
          noteKeys.detail(variables.noteId),
          context.previousNote
        );
      }
    },
    // Always refetch after error or success
    onSettled: (data, error, variables) => {
      queryClient.invalidateQueries({ queryKey: noteKeys.list() });
      queryClient.invalidateQueries({ queryKey: noteKeys.detail(variables.noteId) });
    },
  });
}

/**
 * Hook to delete a note
 */
export function useDeleteNote() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (noteId: string) => {
      try {
        await apiClient.deleteNote(noteId);
        return noteId;
      } catch (error: any) {
        const apiError = error.apiError || handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    // Optimistic update: remove note from cache immediately
    onMutate: async (noteId) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: noteKeys.list() });
      await queryClient.cancelQueries({ queryKey: noteKeys.detail(noteId) });

      // Snapshot the previous values
      const previousNotes = queryClient.getQueryData<NoteWithExtras[]>(noteKeys.list());
      const previousNote = queryClient.getQueryData<Note>(noteKeys.detail(noteId));

      // Optimistically remove the note from the list
      queryClient.setQueryData<NoteWithExtras[]>(noteKeys.list(), (old) => {
        return old?.filter((note) => note.id !== noteId) || [];
      });

      // Remove the single note from cache
      queryClient.removeQueries({ queryKey: noteKeys.detail(noteId) });

      // Return context with snapshotted values
      return { previousNotes, previousNote };
    },
    // If the mutation fails, use the context to roll back
    onError: (err, noteId, context) => {
      if (context?.previousNotes) {
        queryClient.setQueryData(noteKeys.list(), context.previousNotes);
      }
      if (context?.previousNote) {
        queryClient.setQueryData(noteKeys.detail(noteId), context.previousNote);
      }
    },
    // Always refetch after error or success
    onSettled: (data, error, noteId) => {
      queryClient.invalidateQueries({ queryKey: noteKeys.list() });
      queryClient.removeQueries({ queryKey: noteKeys.detail(noteId) });
    },
  });
}
