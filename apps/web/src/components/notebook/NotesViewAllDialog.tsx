'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, FileText, Pencil, Trash2, X } from 'lucide-react';
import type { Note } from '@/hooks/useNotes';
import { useDeleteNote } from '@/hooks/useNotes';
import { formatNoteTitle, formatRelativeTime } from '@/lib/notebook-ui-tokens';

type NotesViewAllDialogProps = {
  open: boolean;
  notes: Note[];
  notebookTitle?: string;
  onClose: () => void;
  onEditNote?: (id: string) => void;
};

export function NotesViewAllDialog({
  open,
  notes,
  notebookTitle,
  onClose,
  onEditNote,
}: NotesViewAllDialogProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const deleteMutation = useDeleteNote();

  if (!open) return null;

  const handleDelete = async (noteId: string) => {
    const confirmed = window.confirm('Delete this note? This cannot be undone.');
    if (!confirmed) return;
    await deleteMutation.mutateAsync(noteId);
    if (expandedId === noteId) setExpandedId(null);
  };

  return (
    <div className="assets-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="assets-modal notebook-notes-dialog"
        role="dialog"
        aria-labelledby="notes-dialog-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 id="notes-dialog-title" className="text-[20px] font-bold text-[var(--color-home-text)]">
              Notebook notes
            </h2>
            <p className="text-[14px] text-[var(--color-home-text-muted)] mt-1">
              {notebookTitle ? `${notebookTitle} · ` : ''}
              {notes.length} note{notes.length === 1 ? '' : 's'}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-[var(--color-brand-surface)] text-[var(--color-home-label)]"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {notes.length === 0 ? (
          <p className="text-[14px] text-[var(--color-home-text-muted)] py-8 text-center">
            No notes in this notebook yet.
          </p>
        ) : (
          <div className="notebook-notes-dialog-grid max-h-[65vh] overflow-y-auto pr-1">
            {notes.map((note) => {
              const expanded = expandedId === note.id;
              const title = formatNoteTitle(note.content);
              const snippet =
                note.content.length > 160 ? `${note.content.slice(0, 160).trim()}…` : note.content;
              return (
                <div
                  key={note.id}
                  className={`notebook-notes-dialog-card ${expanded ? 'notebook-notes-dialog-card--expanded' : ''}`}
                >
                  <div className="flex gap-3">
                    <div className="assets-note-icon flex-shrink-0 w-10 h-10">
                      <FileText className="w-5 h-5 text-[#CA8A04]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <button
                          type="button"
                          className="text-left flex-1 min-w-0"
                          onClick={() => setExpandedId(expanded ? null : note.id)}
                        >
                          <h3 className="text-[15px] font-bold text-[var(--color-home-text)]">{title}</h3>
                        </button>
                        <div className="flex items-center gap-1 flex-shrink-0">
                          {onEditNote && (
                            <button
                              type="button"
                              onClick={() => onEditNote(note.id)}
                              className="p-1.5 rounded-lg hover:bg-[var(--color-brand-surface)] text-[var(--color-home-label)]"
                              title="Edit note"
                              aria-label="Edit note"
                            >
                              <Pencil className="w-3.5 h-3.5" />
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => void handleDelete(note.id)}
                            disabled={deleteMutation.isPending}
                            className="p-1.5 rounded-lg hover:bg-red-50 text-[var(--color-home-label)] hover:text-red-600"
                            title="Delete note"
                            aria-label="Delete note"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => setExpandedId(expanded ? null : note.id)}
                            className="p-1.5 rounded-lg hover:bg-[var(--color-brand-surface)]"
                            aria-label={expanded ? 'Collapse' : 'Expand'}
                          >
                            {expanded ? (
                              <ChevronUp className="w-4 h-4 text-[var(--color-home-label)]" />
                            ) : (
                              <ChevronDown className="w-4 h-4 text-[var(--color-home-label)]" />
                            )}
                          </button>
                        </div>
                      </div>
                      <p className="text-[11px] text-[var(--color-home-label)] mt-0.5">
                        {formatRelativeTime(note.updated_at || note.created_at)}
                      </p>
                      {!expanded && (
                        <p className="text-[13px] text-[var(--color-home-text-muted)] mt-2 line-clamp-2 whitespace-pre-wrap">
                          {snippet}
                        </p>
                      )}
                    </div>
                  </div>
                  {expanded && (
                    <div className="notebook-notes-dialog-body mt-4 pt-4 border-t border-[var(--color-home-border)]">
                      <pre className="text-[13px] text-[var(--color-home-text)] whitespace-pre-wrap font-sans leading-relaxed">
                        {note.content}
                      </pre>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
