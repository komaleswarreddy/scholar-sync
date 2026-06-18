'use client';

import { useEffect, useRef, type ReactNode } from 'react';
import {
  Group,
  Panel,
  Separator,
  useDefaultLayout,
  useGroupRef,
  type Layout,
} from 'react-resizable-panels';
import { useNotebookContext } from '@/contexts/NotebookContext';
import { useOptionalTutorNoteEditor } from '@/contexts/TutorNoteEditorContext';
import { ProblemSolverMobileTabs } from './ProblemSolverMobileTabs';
import { NotebookChatColumn } from './NotebookChatColumn';
import { NotebookRightColumn } from './NotebookRightColumn';
import { NotebookSourcesColumn } from './NotebookSourcesColumn';

const PANEL_STORAGE_ID = 'notebook-workspace-panels-v2';
const PANEL_IDS = ['sources', 'chat', 'studio'] as const;

/** Percentages — numeric props are pixels in react-resizable-panels v4 */
const DEFAULT_LAYOUT = {
  sources: 22,
  chat: 58,
  studio: 20,
};

const TUTOR_NOTE_EDITOR_LAYOUT: Layout = {
  sources: 22,
  chat: 48,
  studio: 30,
};

function PanelShell({ children }: { children: ReactNode }) {
  return <div className="notebook-panel-shell">{children}</div>;
}

function TutorNotePanelLayoutSync({ groupRef }: { groupRef: ReturnType<typeof useGroupRef> }) {
  const { notebook } = useNotebookContext();
  const noteEditor = useOptionalTutorNoteEditor();
  const savedLayoutRef = useRef<Layout | null>(null);

  useEffect(() => {
    if (notebook.mode !== 'tutor' || !noteEditor) return;
    const group = groupRef.current;
    if (!group) return;

    if (noteEditor.isEditorOpen) {
      if (!savedLayoutRef.current) {
        savedLayoutRef.current = group.getLayout();
      }
      group.setLayout(TUTOR_NOTE_EDITOR_LAYOUT);
      return;
    }

    if (savedLayoutRef.current) {
      group.setLayout(savedLayoutRef.current);
      savedLayoutRef.current = null;
    }
  }, [groupRef, noteEditor?.isEditorOpen, notebook.mode, noteEditor]);

  return null;
}

export function NotebookWorkspacePanels() {
  const groupRef = useGroupRef();
  const { defaultLayout, onLayoutChanged } = useDefaultLayout({
    id: PANEL_STORAGE_ID,
    panelIds: [...PANEL_IDS],
    storage: typeof window !== 'undefined' ? localStorage : undefined,
  });

  const layout = defaultLayout ?? DEFAULT_LAYOUT;

  return (
    <>
      <div className="notebook-workspace-panels-desktop">
        <TutorNotePanelLayoutSync groupRef={groupRef} />
        <Group
          id={PANEL_STORAGE_ID}
          orientation="horizontal"
          defaultLayout={layout}
          onLayoutChanged={onLayoutChanged}
          groupRef={groupRef}
          resizeTargetMinimumSize={{ coarse: 28, fine: 10 }}
          className="notebook-workspace-panels"
        >
          <Panel
            id="sources"
            defaultSize="22%"
            minSize="260px"
            maxSize="38%"
            className="notebook-panel"
          >
            <PanelShell>
              <NotebookSourcesColumn />
            </PanelShell>
          </Panel>

          <Separator className="notebook-resize-handle" />

          <Panel id="chat" defaultSize="58%" minSize="500px" className="notebook-panel">
            <PanelShell>
              <NotebookChatColumn />
            </PanelShell>
          </Panel>

          <Separator className="notebook-resize-handle" />

          <Panel
            id="studio"
            defaultSize="20%"
            minSize="280px"
            maxSize="42%"
            className="notebook-panel"
          >
            <PanelShell>
              <NotebookRightColumn />
            </PanelShell>
          </Panel>
        </Group>
      </div>

      <ProblemSolverMobileTabs />
    </>
  );
}
