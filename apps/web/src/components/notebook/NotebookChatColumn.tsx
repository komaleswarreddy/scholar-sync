'use client';



import { ChatInterface } from '@/components/chat/ChatInterface';

import { ProblemSolverChatInterface } from '@/components/problem-solver/chat/ProblemSolverChatInterface';

import { useNotebookContext } from '@/contexts/NotebookContext';

import { useTutorBootstrapOptional } from '@/contexts/TutorBootstrapContext';



export function NotebookChatColumn() {

  const { notebook } = useNotebookContext();



  if (notebook.mode === 'problem_solver') {

    return <ProblemSolverChatInterface />;

  }



  const bootstrapCtx = useTutorBootstrapOptional();

  const tutorScope =

    notebook.mode === 'tutor' && notebook.settings && typeof notebook.settings === 'object'

      ? (notebook.settings.tutor_scope as Record<string, unknown> | undefined)

      : undefined;



  const tutorSuggestions =

    notebook.mode === 'tutor' && bootstrapCtx?.suggestions?.length

      ? bootstrapCtx.suggestions

      : undefined;



  return (

    <main className="notebook-col notebook-col--center notebook-col--embedded flex flex-col min-h-0 h-full">

      <ChatInterface

        mode={notebook.mode === 'tutor' ? 'tutor' : 'dashboard'}

        appearance="notebook"

        defaultNcertScope={tutorScope ?? null}

        tutorSuggestions={tutorSuggestions}

        tutorBootstrapReady={bootstrapCtx?.isReady ?? true}

        tutorBootstrapping={bootstrapCtx?.isBootstrapping ?? false}

        tutorOverviewChatId={bootstrapCtx?.overviewChatId}

      />

    </main>

  );

}


