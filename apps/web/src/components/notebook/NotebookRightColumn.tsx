'use client';

import { RecentAssetsPanel } from '@/components/studio/RecentAssetsPanel';
import { StudioSuite } from '@/components/studio/StudioSuite';
import { NotebookWeeklyMastery } from './NotebookWeeklyMastery';
import { TutorNotebookNotesPanel } from './TutorNotebookNotesPanel';
import { NoteRichEditor } from '@/components/notes/NoteRichEditor';
import { useNotebookContext } from '@/contexts/NotebookContext';
import { useOptionalTutorNoteEditor } from '@/contexts/TutorNoteEditorContext';

export type { TutorActiveNote } from '@/contexts/TutorNoteEditorContext';

function TutorStyleRightPanel({
  onOpenNote,
}: {
  onOpenNote: (noteId: string | 'new' | null) => void;
}) {
  return (
    <aside className="notebook-col notebook-col--right notebook-col--embedded h-full overflow-y-auto flex flex-col min-h-0">
      <div className="notebook-col-section notebook-col-section--studio flex-shrink-0">
        <StudioSuite layout="notebook" />
      </div>
      <div className="notebook-col-section notebook-col-section--notes flex-shrink-0">
        <TutorNotebookNotesPanel onOpenNote={onOpenNote} />
      </div>
      <div className="notebook-col-section notebook-col-section--generated flex-shrink-0 mt-auto">
        <RecentAssetsPanel variant="compact" maxItems={1} />
      </div>
    </aside>
  );
}

export function NotebookRightColumn() {
  const { notebook } = useNotebookContext();
  const isTutor = notebook.mode === 'tutor';
  const isProblemSolver = notebook.mode === 'problem_solver';
  const noteEditor = useOptionalTutorNoteEditor();

  if (isTutor || isProblemSolver) {
    const activeNote = noteEditor?.activeNote ?? null;
    const setActiveNote = noteEditor?.setActiveNote;

    if (activeNote && setActiveNote) {
      return (
        <aside className="notebook-col notebook-col--right notebook-col--embedded notebook-col--note-editor h-full w-full flex flex-col min-h-0 overflow-hidden">
          <NoteRichEditor
            noteId={activeNote === 'new' ? null : activeNote}
            onClose={() => setActiveNote(null)}
          />
        </aside>
      );
    }

    return <TutorStyleRightPanel onOpenNote={setActiveNote ?? (() => {})} />;
  }

  return (
    <aside className="notebook-col notebook-col--right notebook-col--embedded h-full overflow-y-auto flex flex-col min-h-0">
      <div className="notebook-col-section notebook-col-section--studio flex-shrink-0">
        <StudioSuite layout="notebook" />
      </div>
      <div className="notebook-col-section notebook-col-section--generated flex-shrink-0">
        <RecentAssetsPanel />
      </div>
      <NotebookWeeklyMastery />
    </aside>
  );
}
