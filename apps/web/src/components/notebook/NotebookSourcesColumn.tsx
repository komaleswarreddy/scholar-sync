'use client';

import { useState } from 'react';
import { SourceList } from '@/components/sources/SourceList';
import { SourceQuestionBrowser } from '@/components/sources/SourceQuestionBrowser';
import { NotebookNotesSidebar } from './NotebookNotesSidebar';
import { NotebookWeeklyMastery } from './NotebookWeeklyMastery';
import { useNotebookContext } from '@/contexts/NotebookContext';

type ActiveSource = { id: string; title: string } | null;

function ProblemSolverSourcesPanel() {
  const [activeSource, setActiveSource] = useState<ActiveSource>(null);

  if (activeSource) {
    return (
      <aside className="notebook-col notebook-col--left notebook-col--embedded h-full flex flex-col min-h-0">
        <SourceQuestionBrowser
          sourceId={activeSource.id}
          sourceTitle={activeSource.title}
          onBack={() => setActiveSource(null)}
        />
      </aside>
    );
  }

  return (
    <aside className="notebook-col notebook-col--left notebook-col--embedded h-full flex flex-col min-h-0">
      <div className="notebook-col-section notebook-col-section--sources flex flex-col min-h-0">
        <SourceList
          variant="notebook"
          onOpenQuestionPaper={(source) => setActiveSource(source)}
        />
      </div>
      <NotebookWeeklyMastery />
    </aside>
  );
}

export function NotebookSourcesColumn() {
  const { notebook } = useNotebookContext();
  const isTutor = notebook.mode === 'tutor';
  const isProblemSolver = notebook.mode === 'problem_solver';

  if (isProblemSolver) {
    return <ProblemSolverSourcesPanel />;
  }

  if (isTutor) {
    return (
      <aside className="notebook-col notebook-col--left notebook-col--embedded h-full flex flex-col min-h-0">
        <div className="notebook-col-section notebook-col-section--sources flex flex-col min-h-0">
          <SourceList variant="notebook" />
        </div>
        <NotebookWeeklyMastery />
      </aside>
    );
  }

  return (
    <aside className="notebook-col notebook-col--left notebook-col--embedded h-full flex flex-col min-h-0">
      <div className="notebook-col-section notebook-col-section--sources flex flex-col min-h-0">
        <SourceList variant="notebook" />
      </div>
      <NotebookNotesSidebar />
    </aside>
  );
}
