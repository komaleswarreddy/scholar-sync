'use client';

import { useRef, useEffect } from 'react';
import { Loader2, RotateCcw } from 'lucide-react';
import { NotebookChatSelectionPopover } from '@/components/chat/NotebookChatSelectionPopover';
import { RichMarkdown } from '@/components/common/RichMarkdown';
import { useProblemSolverContext } from '@/contexts/ProblemSolverContext';
import { ProblemDNACards } from '../ProblemDNACards';
import { SolvingModeSelector } from '../SolvingModeSelector';
import { CheckpointMCQ } from '../CheckpointMCQ';
import { FollowUpActionBar } from '../FollowUpActionBar';
import { ProblemSolverComposer } from './ProblemSolverComposer';
import styles from '@/components/tutor/tutor-mode.module.css';

function UserMessageBubble({ text }: { text: string }) {
  return (
    <div className="flex justify-end mb-4">
      <div className="notebook-chat-user-bubble max-w-[85%] px-4 py-3 rounded-2xl rounded-br-md bg-[var(--color-brand-primary)] text-white text-sm leading-relaxed whitespace-pre-wrap">
        {text}
      </div>
    </div>
  );
}

function AssistantBubble({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex justify-start mb-4" data-assistant-content="true">
      <div className="notebook-chat-assistant-bubble max-w-[95%] w-full px-4 py-3 rounded-2xl rounded-bl-md bg-surface border border-border-default text-sm">
        {children}
      </div>
    </div>
  );
}

function LoadingBubble({ label }: { label: string }) {
  return (
    <AssistantBubble>
      <div className={styles.loadingRow}>
        <Loader2 className={`w-4 h-4 ${styles.spinner}`} strokeWidth={1.75} />
        {label}
      </div>
    </AssistantBubble>
  );
}

export function ProblemSolverChatInterface() {
  const scrollRef = useRef<HTMLDivElement>(null);
  const {
    session,
    flowStep,
    isLoadingSession,
    streamingSections,
    streamTitle,
    isStreaming,
    isFollowUpLoading,
    streamError,
    pendingCheckpoint,
    followUpButtons,
    resetFlow,
  } = useProblemSolverContext();

  const showModeSelect =
    session?.problem_dna &&
    (flowStep === 'mode_select' || flowStep === 'dna_ready') &&
    !session.last_response;
  const showResponse =
    streamingSections.length > 0 ||
    isStreaming ||
    Boolean(session?.last_response?.sections?.length);
  const responseSections =
    streamingSections.length > 0
      ? streamingSections
      : session?.last_response?.sections ?? [];
  const responseTitle = streamTitle || session?.last_response?.title;
  const dnaCompact = Boolean(session?.solving_mode || session?.last_response);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [
    session?.session_id,
    session?.solving_mode,
    streamingSections.length,
    flowStep,
    pendingCheckpoint,
    followUpButtons.length,
  ]);

  return (
    <main className="notebook-col notebook-col--center notebook-col--embedded flex flex-col min-h-0 h-full">
      <header className={`${styles.psFlowHeader} px-4 pt-4 pb-2 flex-shrink-0 border-b border-border-default`}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className={styles.psFlowTitle}>Guided Problem Solver</h1>
            <p className={styles.psFlowSubtitle}>
              Paste a problem, pick how you want help, and get step-by-step guidance.
            </p>
          </div>
          {session ? (
            <button
              type="button"
              className={styles.psSecondaryBtn}
              onClick={() => void resetFlow()}
            >
              <RotateCcw className="w-4 h-4" strokeWidth={1.75} />
              New problem
            </button>
          ) : null}
        </div>
      </header>

      <div
        ref={scrollRef}
        className="flex-1 min-h-0 overflow-y-auto px-4 py-4 notebook-chat-messages"
      >
        {isLoadingSession ? <LoadingBubble label="Loading session…" /> : null}

        {!session && !isLoadingSession ? (
          <AssistantBubble>
            <p className="text-text-secondary text-sm">
              Type or paste your problem in the box below. You can also attach an image or PDF.
            </p>
          </AssistantBubble>
        ) : null}

        {session?.problem_text ? (
          <UserMessageBubble text={session.problem_text_normalized || session.problem_text} />
        ) : null}

        {flowStep === 'extracting' ? <LoadingBubble label="Extracting text from your file…" /> : null}
        {flowStep === 'dna_loading' ? <LoadingBubble label="Analyzing problem DNA…" /> : null}

        {session?.problem_dna ? (
          <AssistantBubble>
            {!dnaCompact ? (
              <ProblemDNACards dna={session.problem_dna} />
            ) : (
              <>
                <p className="text-xs font-semibold text-text-secondary mb-2">Problem DNA</p>
                <ProblemDNACards dna={session.problem_dna} compact />
              </>
            )}
          </AssistantBubble>
        ) : null}

        {showModeSelect ? (
          <AssistantBubble>
            <SolvingModeSelector />
          </AssistantBubble>
        ) : null}

        {showResponse ? (
          <AssistantBubble>
            {responseTitle ? (
              <h3 className="font-semibold text-text-primary mb-3">{responseTitle}</h3>
            ) : null}
            {(isStreaming || isFollowUpLoading) && !responseSections.length ? (
              <div className={styles.loadingRow}>
                <Loader2 className={`w-4 h-4 ${styles.spinner}`} strokeWidth={1.75} />
                Generating response…
              </div>
            ) : null}
            <div className={styles.psResponseBody}>
              {responseSections.map((section, idx) => (
                <div key={`${section.heading}-${idx}`} className={styles.psResponseSection}>
                  {section.heading ? (
                    <h4 className={styles.psResponseHeading}>{section.heading}</h4>
                  ) : null}
                  <RichMarkdown content={section.bodyMarkdown} variant="problem-solver" />
                </div>
              ))}
            </div>
            {session?.last_response?.finalAnswer ? (
              <div className={styles.psFinalAnswer}>
                <p className={styles.psFinalAnswerLabel}>Final answer</p>
                <RichMarkdown
                  content={session.last_response.finalAnswer}
                  variant="problem-solver"
                />
              </div>
            ) : null}
          </AssistantBubble>
        ) : null}

        {flowStep === 'checkpoint' && pendingCheckpoint ? (
          <AssistantBubble>
            <CheckpointMCQ checkpoint={pendingCheckpoint} />
          </AssistantBubble>
        ) : null}

        {flowStep === 'follow_up' && followUpButtons.length > 0 ? (
          <AssistantBubble>
            <FollowUpActionBar buttons={followUpButtons} />
          </AssistantBubble>
        ) : null}

        {streamError ? <p className={styles.psError}>{streamError}</p> : null}

        <NotebookChatSelectionPopover scrollContainerRef={scrollRef} />
      </div>

      <ProblemSolverComposer />
    </main>
  );
}
