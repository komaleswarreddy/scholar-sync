'use client';

import { useEffect, useRef, useState, type ReactNode } from 'react';
import { ChevronDown } from 'lucide-react';
import { notePreviewTitle, parseNoteContent, serializeNoteContent, escapeHtml } from '@/lib/note-content';
import type { NoteWithExtras } from '@/hooks/useNotes';

type NoteCreateOrAppendMenuProps = {
  notes: NoteWithExtras[];
  onCreateNew: () => void;
  onAppendToNote: (noteId: string, content: string) => Promise<void>;
  appendContent: string;
  triggerLabel: string;
  triggerClassName?: string;
  children?: ReactNode;
};

export function NoteCreateOrAppendMenu({
  notes,
  onCreateNew,
  onAppendToNote,
  appendContent,
  triggerLabel,
  triggerClassName = 'notebook-link-btn',
}: NoteCreateOrAppendMenuProps) {
  const [open, setOpen] = useState(false);
  const [appendingId, setAppendingId] = useState<string | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDocMouseDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onDocMouseDown);
    return () => document.removeEventListener('mousedown', onDocMouseDown);
  }, [open]);

  if (notes.length === 0) {
    return (
      <button type="button" className={triggerClassName} onClick={onCreateNew}>
        {triggerLabel}
      </button>
    );
  }

  const handleAppend = async (noteId: string) => {
    if (appendingId) return;
    setAppendingId(noteId);
    try {
      await onAppendToNote(noteId, appendContent);
      setOpen(false);
    } finally {
      setAppendingId(null);
    }
  };

  return (
    <div className="relative inline-flex" ref={rootRef}>
      <button
        type="button"
        className={`${triggerClassName} inline-flex items-center gap-1`}
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        aria-haspopup="menu"
      >
        {triggerLabel}
        <ChevronDown className={`w-3.5 h-3.5 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="notebook-note-append-menu" role="menu">
          <button
            type="button"
            role="menuitem"
            className="notebook-note-append-menu-item"
            onClick={() => {
              setOpen(false);
              onCreateNew();
            }}
          >
            Create new note
          </button>
          {appendContent.trim().length > 0 && (
            <>
              <p className="notebook-note-append-menu-label">Append to…</p>
              {notes.slice(0, 8).map((note) => (
                <button
                  key={note.id}
                  type="button"
                  role="menuitem"
                  className="notebook-note-append-menu-item"
                  disabled={appendingId === note.id}
                  onClick={() => void handleAppend(note.id)}
                >
                  {appendingId === note.id ? 'Adding…' : notePreviewTitle(note.content)}
                </button>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export async function buildAppendedNoteContent(existingContent: string, selectionPlain: string) {
  const parsed = parseNoteContent(existingContent);
  const snippet = escapeHtml(selectionPlain.trim());
  const appendedBody = parsed.bodyHtml
    ? `${parsed.bodyHtml}<hr/><p>${snippet}</p>`
    : `<p>${snippet}</p>`;
  return serializeNoteContent(parsed.title, appendedBody);
}
