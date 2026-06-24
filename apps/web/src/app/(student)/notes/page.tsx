'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { NotesListSkeleton } from '@/components/skeleton';
import { useNotes } from '@/hooks/useNotes';
import { getNoteFlags, toggleNoteFlag } from '@/lib/note-metadata';
import { track } from '@/lib/telemetry';
import { ArrowRight, Filter, Bookmark, BookOpenText } from 'lucide-react';

type NotesFilter = 'all' | 'bms' | 'shorts' | 'gl';

function isShort(content: string) {
  // V1 heuristic: “short note” == concise text
  return content.trim().length > 0 && content.trim().length <= 280;
}

function isGeneratedV1(note: { source_ref_id?: string }, flags: { generated?: boolean }) {
  // V1 heuristic: source-backed notes are likely “generated”; allow user override via metadata.
  if (flags.generated === true) return true;
  if (flags.generated === false) return false;
  return Boolean(note.source_ref_id);
}

export default function NotesPage() {
  const router = useRouter();
  const { data: notes = [], isLoading, error } = useNotes();
  const [filter, setFilter] = useState<NotesFilter>('all');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [advanced, setAdvanced] = useState({
    bookmarkedOnly: false,
    sourceBackedOnly: false,
  });
  const [, forceRerender] = useState(0);

  useEffect(() => {
    track('notes.viewed');
  }, []);

  useEffect(() => {
    track('notes.filtered', { filter, advanced });
  }, [filter, advanced]);

  const filtered = useMemo(() => {
    const base = [...notes].sort(
      (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    );

    return base.filter((n) => {
      const flags = getNoteFlags(n.id);
      const bookmarked = Boolean(flags.bookmarked);
      const short = isShort(n.content || '');
      const generated = isGeneratedV1(n, flags);

      if (advanced.bookmarkedOnly && !bookmarked) return false;
      if (advanced.sourceBackedOnly && !n.source_ref_id) return false;

      if (filter === 'all') return true;
      if (filter === 'bms') return bookmarked;
      if (filter === 'shorts') return short;
      if (filter === 'gl') return generated;
      return true;
    });
  }, [notes, filter, advanced]);

  const openInWorkspace = () => {
    router.push('/dashboard');
  };

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
          <div className="flex items-start justify-between gap-6 mb-6">
            <div>
              <div className="flex items-center gap-2">
                <BookOpenText className="w-5 h-5 text-text-secondary" />
                <h2 className="text-2xl font-semibold text-text-primary">Notes</h2>
              </div>
              <p className="text-text-secondary mt-2">
                Browse and filter your notes. Open the workspace to create new ones.
              </p>
            </div>
            <Button variant="secondary" onClick={openInWorkspace} className="flex items-center gap-2">
              Open workspace
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>

          {/* Filter chips */}
          <div className="flex flex-wrap items-center gap-2 mb-4">
            <Button
              variant={filter === 'all' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setFilter('all')}
            >
              All
            </Button>
            <Button
              variant={filter === 'bms' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setFilter('bms')}
            >
              BMs
            </Button>
            <Button
              variant={filter === 'shorts' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setFilter('shorts')}
            >
              Shorts
            </Button>
            <Button
              variant={filter === 'gl' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setFilter('gl')}
              title="Generated vs Local (V1)"
            >
              G/L
            </Button>
            <Button
              variant={showAdvanced ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setShowAdvanced((v) => !v)}
              className="flex items-center gap-2"
            >
              <Filter className="w-4 h-4" />
              Fltrs
            </Button>
          </div>

          {/* Advanced filters */}
          {showAdvanced ? (
            <Card className="p-4 mb-6">
              <div className="flex flex-wrap items-center gap-3">
                <label className="flex items-center gap-2 text-sm text-text-secondary">
                  <input
                    type="checkbox"
                    checked={advanced.bookmarkedOnly}
                    onChange={(e) => setAdvanced((a) => ({ ...a, bookmarkedOnly: e.target.checked }))}
                  />
                  Bookmarked only
                </label>
                <label className="flex items-center gap-2 text-sm text-text-secondary">
                  <input
                    type="checkbox"
                    checked={advanced.sourceBackedOnly}
                    onChange={(e) => setAdvanced((a) => ({ ...a, sourceBackedOnly: e.target.checked }))}
                  />
                  Source-backed only
                </label>
                <p className="text-xs text-text-tertiary">
                  V1 filters are client-derived and future-ready for persistence.
                </p>
              </div>
            </Card>
          ) : null}

          {/* Content */}
          {isLoading && notes.length === 0 ? (
            <NotesListSkeleton />
          ) : error ? (
            <Card className="p-6">
              <p className="text-text-secondary">Failed to load notes.</p>
              <p className="text-text-tertiary text-sm mt-2">{String((error as any)?.message || error)}</p>
            </Card>
          ) : filtered.length === 0 ? (
            <Card className="p-6">
              <p className="text-text-secondary">No notes match these filters.</p>
              <p className="text-text-tertiary text-sm mt-2">
                Create notes from your workspace or adjust filters.
              </p>
              <div className="mt-4">
                <Button variant="secondary" onClick={openInWorkspace}>
                  Go to workspace
                </Button>
              </div>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filtered.map((n) => {
                const flags = getNoteFlags(n.id);
                const bookmarked = Boolean(flags.bookmarked);
                return (
                  <Card
                    key={n.id}
                    hover
                    onClick={openInWorkspace}
                    className="p-5"
                    title="Open workspace"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-base font-semibold text-text-primary truncate">{n.title}</p>
                        <p className="text-sm text-text-secondary mt-2 line-clamp-3">{n.content}</p>
                        <p className="text-xs text-text-tertiary mt-3">
                          Updated {new Date(n.updated_at).toLocaleString()}
                        </p>
                      </div>
                      <button
                        className="p-2 rounded-full hover:bg-surface-hover transition-colors"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleNoteFlag(n.id, 'bookmarked');
                          forceRerender((x) => x + 1);
                        }}
                        title={bookmarked ? 'Remove bookmark' : 'Bookmark'}
                        aria-label={bookmarked ? 'Remove bookmark' : 'Bookmark'}
                      >
                        <Bookmark className={`w-4 h-4 ${bookmarked ? 'text-accent-blue' : 'text-text-tertiary'}`} />
                      </button>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
    </div>
  );
}

