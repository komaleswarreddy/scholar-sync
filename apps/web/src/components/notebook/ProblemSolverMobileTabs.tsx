'use client';

import { useEffect, useState } from 'react';
import { useNotebookContext } from '@/contexts/NotebookContext';
import { NotebookChatColumn } from './NotebookChatColumn';
import { NotebookRightColumn } from './NotebookRightColumn';
import { NotebookSourcesColumn } from './NotebookSourcesColumn';

type MobileTab = 'chat' | 'sources' | 'studio';

export function ProblemSolverMobileTabs() {
  const { notebook } = useNotebookContext();
  const [activeTab, setActiveTab] = useState<MobileTab>('chat');

  useEffect(() => {
    const focusChat = () => setActiveTab('chat');
    window.addEventListener('problemSolverFocusChat', focusChat);
    return () => window.removeEventListener('problemSolverFocusChat', focusChat);
  }, []);

  if (notebook.mode !== 'problem_solver') {
    return (
      <div className="notebook-workspace-panels-mobile">
        <div className="notebook-workspace-panels notebook-workspace-panels--chat-only">
          <NotebookChatColumn />
        </div>
      </div>
    );
  }

  return (
    <div className="notebook-workspace-panels-mobile flex flex-col min-h-0 h-full">
      <div className="flex border-b border-border-default bg-surface flex-shrink-0">
        {(
          [
            { id: 'chat' as const, label: 'Chat' },
            { id: 'sources' as const, label: 'Sources' },
            { id: 'studio' as const, label: 'Studio' },
          ] as const
        ).map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`flex-1 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-[var(--color-brand-primary)] text-[var(--color-brand-text)]'
                : 'border-transparent text-text-secondary'
            }`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="flex-1 min-h-0 overflow-hidden">
        {activeTab === 'chat' ? <NotebookChatColumn /> : null}
        {activeTab === 'sources' ? (
          <div className="h-full overflow-y-auto">
            <NotebookSourcesColumn />
          </div>
        ) : null}
        {activeTab === 'studio' ? (
          <div className="h-full overflow-y-auto">
            <NotebookRightColumn />
          </div>
        ) : null}
      </div>
    </div>
  );
}
