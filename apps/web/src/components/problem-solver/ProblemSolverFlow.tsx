'use client';

import { Loader2, RotateCcw } from 'lucide-react';
import { useProblemSolverContext } from '@/contexts/ProblemSolverContext';
import { ProblemIntakePanel } from './ProblemIntakePanel';
import { ProblemDNACards } from './ProblemDNACards';
import { SolvingModeSelector } from './SolvingModeSelector';
import { ModeResponseView } from './ModeResponseView';
import { CheckpointMCQ } from './CheckpointMCQ';
import { FollowUpActionBar } from './FollowUpActionBar';
import styles from '@/components/tutor/tutor-mode.module.css';

export function ProblemSolverFlow() {
  const {
    session,
    flowStep,
    isLoadingSession,
    streamingSections,
    streamTitle,
    streamStatus,
    isStreaming,
    isFollowUpLoading,
    streamError,
    pendingCheckpoint,
    followUpButtons,
    resetFlow,
  } = useProblemSolverContext();

  const showIntake =
    flowStep === 'idle_intake' ||
    flowStep === 'extracting' ||
    (!session && !isLoadingSession);
  const showDna = session?.problem_dna && flowStep !== 'idle_intake';
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
  const responseStatusMessage = streamStatus
    ? `${streamStatus.message} (${Math.max(1, Math.round(streamStatus.elapsedMs / 1000))}s)`
    : null;

  return (
    <main className="notebook-col notebook-col--center notebook-col--embedded flex flex-col min-h-0 h-full">
      <div className={`${styles.tutorRoot} flex-1 min-h-0`}>
        <div className={styles.psFlowWrap}>
          <header className={styles.psFlowHeader}>
            <div>
              <h1 className={styles.psFlowTitle}>Guided Problem Solver</h1>
              <p className={styles.psFlowSubtitle}>
                NCERT-grounded help — upload a problem, pick a solving mode, get structured guidance.
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
          </header>

          {isLoadingSession ? (
            <div className={styles.loadingRow}>
              <Loader2 className={`w-4 h-4 ${styles.spinner}`} strokeWidth={1.75} />
              Loading session…
            </div>
          ) : null}

          {flowStep === 'extracting' ? (
            <div className={styles.loadingRow}>
              <Loader2 className={`w-4 h-4 ${styles.spinner}`} strokeWidth={1.75} />
              Extracting text from your file…
            </div>
          ) : null}

          {flowStep === 'dna_loading' ? (
            <div className={styles.loadingRow}>
              <Loader2 className={`w-4 h-4 ${styles.spinner}`} strokeWidth={1.75} />
              Analyzing problem DNA…
            </div>
          ) : null}

          {showIntake && flowStep !== 'dna_loading' && flowStep !== 'extracting' ? (
            <ProblemIntakePanel />
          ) : null}

          {showDna && session.problem_dna ? (
            <ProblemDNACards dna={session.problem_dna} />
          ) : null}

          {showModeSelect ? <SolvingModeSelector /> : null}

          {showResponse ? (
            <ModeResponseView
              title={responseTitle}
              sections={responseSections}
              isStreaming={isStreaming || isFollowUpLoading}
              finalAnswer={session?.last_response?.finalAnswer}
              statusMessage={responseStatusMessage}
            />
          ) : null}

          {flowStep === 'checkpoint' && pendingCheckpoint ? (
            <CheckpointMCQ checkpoint={pendingCheckpoint} />
          ) : null}

          {flowStep === 'follow_up' && followUpButtons.length > 0 ? (
            <FollowUpActionBar buttons={followUpButtons} />
          ) : null}

          {streamError ? <p className={styles.psError}>{streamError}</p> : null}
        </div>
      </div>
    </main>
  );
}
