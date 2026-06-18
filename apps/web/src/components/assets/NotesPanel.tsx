'use client';

import { useMemo, useState } from 'react';
import {
  ASSET_CLASS_FILTERS,
  ASSET_SUBJECT_FILTERS,
  NOTE_SORT_OPTIONS,
  type AssetClass,
  type AssetSubject,
  type StudyNote,
} from '@/lib/assets-mock-data';
import { formatRelativeTime } from '@/lib/library-mapper';
import { useAppToast } from '@/contexts/AppToastContext';
import { NoteModal } from '@/components/notes/NoteModal';
import { useDeleteNote, useNotes, useUpdateNote } from '@/hooks/useNotes';
import { useListNotebooks } from '@/hooks/useNotebooks';
import { AssetDeleteDialog } from './AssetDeleteDialog';
import { AssetEditModal } from './AssetEditModal';
import { AssetsSortDropdown } from './AssetsSortDropdown';
import { FilterPillRow } from './FilterPillRow';
import { NoteAssetCard } from './NoteAssetCard';

type NotesPanelProps = {
  sort?: (typeof NOTE_SORT_OPTIONS)[number];
  onSortChange?: (value: (typeof NOTE_SORT_OPTIONS)[number]) => void;
  query?: string;
};

export function NotesPanel({
  sort: controlledSort,
  onSortChange,
  query: controlledQuery,
}: NotesPanelProps = {}) {
  const { data: apiNotes = [], isLoading } = useNotes();
  const { data: notebookList } = useListNotebooks();
  const deleteNote = useDeleteNote();
  const updateNote = useUpdateNote();
  const { showToast } = useAppToast();

  const notebookLookup = useMemo(() => {
    const map = new Map<string, { title: string; subject?: string | null; class_level?: string | null }>();
    for (const nb of notebookList?.notebooks ?? []) {
      map.set(nb.id, {
        title: nb.title,
        subject: nb.subject,
        class_level: nb.class_level,
      });
    }
    return map;
  }, [notebookList?.notebooks]);

  const notes = useMemo<StudyNote[]>(
    () =>
      apiNotes.map((note) => {
        const nb = note.notebook_id ? notebookLookup.get(note.notebook_id) : undefined;
        return {
          id: note.id,
          title: note.title,
          notebook: nb?.title ?? 'Notebook',
          subject: nb?.subject ?? '—',
          classLevel: nb?.class_level ?? '—',
          snippet: note.content?.slice(0, 120) || '',
          timestamp: formatRelativeTime(note.updated_at || note.created_at),
        };
      }),
    [apiNotes, notebookLookup],
  );

  const [pinnedIds, setPinnedIds] = useState<Set<string>>(new Set());
  const [viewingNoteId, setViewingNoteId] = useState<string | null>(null);
  const [editing, setEditing] = useState<StudyNote | null>(null);
  const [deleting, setDeleting] = useState<StudyNote | null>(null);
  const [localTitles, setLocalTitles] = useState<Record<string, string>>({});

  const [subjectFilter, setSubjectFilter] =
    useState<(typeof ASSET_SUBJECT_FILTERS)[number]>('All Subjects');
  const [classFilter, setClassFilter] = useState<(typeof ASSET_CLASS_FILTERS)[number]>('All Classes');
  const [internalSort, setInternalSort] =
    useState<(typeof NOTE_SORT_OPTIONS)[number]>('Most recent');
  const sort = controlledSort ?? internalSort;
  const setSort = onSortChange ?? setInternalSort;
  const query = controlledQuery ?? '';

  const displayNotes = useMemo(
    () =>
      notes.map((note) => ({
        ...note,
        title: localTitles[note.id] ?? note.title,
      })),
    [notes, localTitles],
  );

  const filtered = useMemo(() => {
    let list = displayNotes.filter((n) => {
      if (subjectFilter !== 'All Subjects' && n.subject !== (subjectFilter as AssetSubject)) {
        return false;
      }
      if (classFilter !== 'All Classes' && n.classLevel !== (classFilter as AssetClass)) {
        return false;
      }
      if (query.trim()) {
        const hay = [n.title, n.notebook, n.subject, n.snippet].join(' ').toLowerCase();
        if (!hay.includes(query.trim().toLowerCase())) return false;
      }
      return true;
    });

    if (sort === 'Title A–Z') {
      list = [...list].sort((a, b) => a.title.localeCompare(b.title));
    } else if (sort === 'Oldest first') {
      list = [...list].reverse();
    }

    return [...list].sort((a, b) => {
      const ap = pinnedIds.has(a.id) ? 0 : 1;
      const bp = pinnedIds.has(b.id) ? 0 : 1;
      if (ap !== bp) return ap - bp;
      return 0;
    });
  }, [displayNotes, subjectFilter, classFilter, sort, pinnedIds, query]);

  const togglePin = (id: string, title: string) => {
    setPinnedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
        showToast(`"${title}" unpinned`);
      } else {
        next.add(id);
        showToast(`"${title}" pinned to top`);
      }
      return next;
    });
  };

  const saveEdit = (newTitle: string) => {
    if (!editing) return;
    setLocalTitles((prev) => ({ ...prev, [editing.id]: newTitle }));
    showToast('Note updated');
    setEditing(null);
  };

  const viewingNote = useMemo(
    () => apiNotes.find((note) => note.id === viewingNoteId) ?? null,
    [apiNotes, viewingNoteId],
  );

  const handleOpenNote = (noteId: string) => {
    setViewingNoteId(noteId);
  };

  const handleSaveNote = async (content: string) => {
    if (!viewingNoteId) return;
    await updateNote.mutateAsync({ noteId: viewingNoteId, content });
    setViewingNoteId(null);
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    try {
      await deleteNote.mutateAsync(deleting.id);
      setPinnedIds((prev) => {
        const next = new Set(prev);
        next.delete(deleting.id);
        return next;
      });
      showToast(`"${deleting.title}" deleted`);
    } catch {
      showToast('Could not delete note');
    }
    setDeleting(null);
  };

  return (
    <div className="assets-panel" role="tabpanel">
      <div className="assets-filters-toolbar assets-filters-toolbar--notes">
        <div className="assets-filters-stack assets-filters-stack--notes">
          <FilterPillRow
            label="Filter by class"
            options={ASSET_CLASS_FILTERS}
            value={classFilter}
            onChange={(value) => setClassFilter(value as typeof classFilter)}
          />
          <FilterPillRow
            label="Filter by subject"
            options={ASSET_SUBJECT_FILTERS}
            value={subjectFilter}
            onChange={(value) => setSubjectFilter(value as typeof subjectFilter)}
          />
        </div>
        <AssetsSortDropdown value={sort} onChange={setSort} className="assets-filters-sort" />
      </div>

      {isLoading ? (
        <p className="text-center text-[var(--color-home-text-muted)] py-10 text-[15px]">
          Loading notes...
        </p>
      ) : filtered.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {filtered.map((note) => (
            <NoteAssetCard
              key={note.id}
              note={note}
              isPinned={pinnedIds.has(note.id)}
              onOpen={() => handleOpenNote(note.id)}
              onPin={() => togglePin(note.id, note.title)}
              onEdit={() => handleOpenNote(note.id)}
              onDelete={() => setDeleting(note)}
            />
          ))}
        </div>
      ) : (
        <p className="text-center text-[var(--color-home-text-muted)] py-10 text-[15px]">
          No notes match your filters.
        </p>
      )}

      {viewingNote ? (
        <NoteModal
          isOpen={!!viewingNoteId}
          onClose={() => setViewingNoteId(null)}
          noteId={viewingNoteId}
          initialContent={viewingNote.content}
          title={viewingNote.title}
          isSaving={updateNote.isPending}
          onSave={handleSaveNote}
        />
      ) : null}

      <AssetEditModal
        open={!!editing}
        title={editing?.title ?? ''}
        itemType="note"
        onClose={() => setEditing(null)}
        onSave={saveEdit}
      />
      <AssetDeleteDialog
        open={!!deleting}
        itemName={deleting?.title ?? ''}
        itemType="note"
        onClose={() => setDeleting(null)}
        onConfirm={confirmDelete}
      />
    </div>
  );
}
