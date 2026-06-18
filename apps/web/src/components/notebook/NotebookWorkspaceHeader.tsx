'use client';

import { ArrowLeft } from 'lucide-react';
import { useNotebookContext } from '@/contexts/NotebookContext';
import { useNotebookLeaveGuard } from '@/contexts/NotebookLeaveGuardContext';

export function NotebookWorkspaceHeader() {
  const { title, setTitle } = useNotebookContext();
  const { tryNavigate } = useNotebookLeaveGuard();

  return (
    <header className="notebook-workspace-header notebook-workspace-header--minimal">
      <button
        type="button"
        onClick={() => tryNavigate('/library')}
        className="notebook-workspace-back"
        aria-label="Back to library"
      >
        <ArrowLeft className="w-3.5 h-3.5" strokeWidth={1.75} />
        <span>Back</span>
      </button>

      <input
        className="notebook-workspace-title-input"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        aria-label="Notebook title"
      />
    </header>
  );
}
