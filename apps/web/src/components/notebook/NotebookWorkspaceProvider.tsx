'use client';



import type { ReactNode } from 'react';

import { ChatProvider } from '@/contexts/ChatContext';

import { NotebookProvider, type NotebookRecord } from '@/contexts/NotebookContext';

import { NotebookLeaveGuard } from '@/contexts/NotebookLeaveGuardContext';

import { SourceProvider } from '@/contexts/SourceContext';

import { TutorSourceBootstrap } from '@/components/notebook/TutorSourceBootstrap';

import { TutorChatBootstrap } from '@/components/notebook/TutorChatBootstrap';

import { TutorStudioBootstrap } from '@/components/notebook/TutorStudioBootstrap';

import { TutorBootstrapProvider } from '@/contexts/TutorBootstrapContext';

import { StudioChatBridgeProvider } from '@/contexts/StudioChatBridgeContext';

import { StudioPreviewProvider } from '@/contexts/StudioPreviewContext';

import { StudioGenerationProvider } from '@/contexts/StudioGenerationContext';

import { TutorNoteEditorProvider } from '@/contexts/TutorNoteEditorContext';

import { UserProvider } from '@/contexts/UserContext';

import { ProblemSolverProvider } from '@/contexts/ProblemSolverContext';



function StandardNotebookProviders({ children }: { children: ReactNode }) {

  return (

    <TutorBootstrapProvider>

      <TutorSourceBootstrap />

      <TutorChatBootstrap />

      <ChatProvider>

        <StudioChatBridgeProvider>

          <StudioPreviewProvider>

            <StudioGenerationProvider>

              <TutorStudioBootstrap />

              <TutorNoteEditorProvider>{children}</TutorNoteEditorProvider>

            </StudioGenerationProvider>

          </StudioPreviewProvider>

        </StudioChatBridgeProvider>

      </ChatProvider>

    </TutorBootstrapProvider>

  );

}



export function NotebookWorkspaceProvider({

  notebook,

  children,

}: {

  notebook: NotebookRecord;

  children: ReactNode;

}) {

  const isProblemSolver = notebook.mode === 'problem_solver';

  return (

    <UserProvider>

      <NotebookProvider notebook={notebook}>

        <NotebookLeaveGuard>

          <SourceProvider>
            <StandardNotebookProviders>
              {isProblemSolver ? (
                <ProblemSolverProvider>{children}</ProblemSolverProvider>
              ) : (
                children
              )}
            </StandardNotebookProviders>
          </SourceProvider>

        </NotebookLeaveGuard>

      </NotebookProvider>

    </UserProvider>

  );

}


