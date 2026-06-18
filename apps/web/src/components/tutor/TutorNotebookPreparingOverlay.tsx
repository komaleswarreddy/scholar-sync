'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, Check, Loader2, Sparkles } from 'lucide-react';
import styles from '@/components/tutor/tutor-mode.module.css';
import {
  formatAssetStepLabel,
  MAX_WAIT_MS,
  PREPARE_STEP_LABELS,
  prepareTutorNotebook,
  shouldEnterNotebookAfterPrepare,
  TutorPrepareFailedError,
  type PrepareProgress,
  type PrepareStepId,
  type TutorPrepareScope,
} from '@/lib/tutor-notebook-prepare';

function scopeFingerprint(scope: TutorPrepareScope): string {
  return [
    scope.classNum,
    scope.subjectKey,
    scope.chapterNo,
    scope.conceptId,
    scope.filterChapterName ?? scope.chapterTitle,
  ].join('|');
}

const STEP_ORDER: PrepareStepId[] = [
  'creating_notebook',
  'building_summary',
  'generating_assets',
  'finalizing',
];

type TutorNotebookPreparingOverlayProps = {
  scope: TutorPrepareScope;
  onReady: (payload: { slug: string; partialFailure: boolean; timedOut: boolean }) => void;
  onHardFail: (message: string) => void;
  onCancel: () => void;
};

function buildInitialProgress(scope: TutorPrepareScope): PrepareProgress {
  const parts = [
    scope.classNum != null ? `Class ${scope.classNum}` : null,
    scope.subjectLabel,
    scope.chapterNo != null ? `Ch. ${scope.chapterNo} ${scope.chapterTitle}` : null,
    scope.conceptId !== 'all' ? scope.conceptLabel : null,
  ].filter(Boolean);

  return {
    step: 'creating_notebook',
    stepIndex: 0,
    totalSteps: STEP_ORDER.length,
    progress: 4,
    elapsedMs: 0,
    estimatedRemainingMs: 53_000,
    contextLabel: parts.join(' · '),
  };
}

export function TutorNotebookPreparingOverlay({
  scope,
  onReady,
  onHardFail,
  onCancel,
}: TutorNotebookPreparingOverlayProps) {
  const [progress, setProgress] = useState<PrepareProgress>(() => buildInitialProgress(scope));
  const [failed, setFailed] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);
  const [clockMs, setClockMs] = useState(0);

  const onReadyRef = useRef(onReady);
  const onHardFailRef = useRef(onHardFail);
  const runIdRef = useRef(0);

  useEffect(() => {
    onReadyRef.current = onReady;
    onHardFailRef.current = onHardFail;
  }, [onHardFail, onReady]);

  useEffect(() => {
    const startedAt = Date.now();
    setClockMs(0);
    const timer = window.setInterval(() => {
      setClockMs(Date.now() - startedAt);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [retryKey, scope]);

  const scopeKey = scopeFingerprint(scope);

  useEffect(() => {
    const runId = runIdRef.current + 1;
    runIdRef.current = runId;
    let cancelled = false;
    const controller = new AbortController();

    const run = async () => {
      setFailed(false);
      setErrorMessage(null);
      setProgress(buildInitialProgress(scope));
      const startedAt = Date.now();

      try {
        const result = await prepareTutorNotebook(
          scope,
          (next) => {
            if (!cancelled && runIdRef.current === runId) {
              setProgress(next);
            }
          },
          { signal: controller.signal },
        );

        if (cancelled || runIdRef.current !== runId) return;

        const elapsedMs = Date.now() - startedAt;
        if (!shouldEnterNotebookAfterPrepare(result, elapsedMs)) {
          const waitMs = Math.max(0, MAX_WAIT_MS - elapsedMs);
          if (waitMs > 0) {
            await new Promise((resolve) => setTimeout(resolve, waitMs));
          }
        }

        if (cancelled || runIdRef.current !== runId) return;
        onReadyRef.current({
          slug: result.slug,
          partialFailure: result.partialFailure || result.assetsCreated < 2,
          timedOut: result.timedOut || elapsedMs >= MAX_WAIT_MS,
        });
      } catch (error) {
        if (cancelled || runIdRef.current !== runId) return;
        if ((error as { name?: string }).name === 'AbortError' || (error as { code?: string }).code === 'ERR_CANCELED') {
          return;
        }
        const message =
          error instanceof TutorPrepareFailedError
            ? error.message
            : 'Something went wrong while preparing your notebook.';
        setFailed(true);
        setErrorMessage(message);
        onHardFailRef.current(message);
      }
    };

    void run();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [scopeKey, retryKey, scope]);

  const assetTypes = progress?.assetTypes;
  const activeStepIndex = progress?.stepIndex ?? 0;

  const elapsedLabel = useMemo(() => {
    const ms = progress?.elapsedMs ? Math.max(progress.elapsedMs, clockMs) : clockMs;
    const seconds = Math.floor(ms / 1000);
    return `${seconds}s`;
  }, [clockMs, progress?.elapsedMs]);

  const remainingLabel = useMemo(() => {
    if (!progress) return '~55s';
    const seconds = Math.max(0, Math.ceil(progress.estimatedRemainingMs / 1000));
    return seconds > 0 ? `~${seconds}s left` : 'Almost done';
  }, [progress]);

  return (
    <div className={styles.prepareOverlay} role="dialog" aria-modal="true" aria-labelledby="prepare-title">
      <div className={styles.prepareCard}>
        <div className={styles.prepareHeader}>
          <div className={styles.prepareIconWrap}>
            <Sparkles className="w-5 h-5" strokeWidth={1.75} aria-hidden />
          </div>
          <div className={styles.prepareHeaderText}>
            <h2 id="prepare-title" className={styles.prepareTitle}>
              Preparing your notebook
            </h2>
            <p className={styles.prepareSubtitle}>
              Building your chapter summary and study assets before you enter.
            </p>
          </div>
        </div>

        {progress?.contextLabel ? (
          <div className={styles.prepareContextChip}>{progress.contextLabel}</div>
        ) : null}

        <div className={styles.prepareProgressSection}>
          <div className={styles.prepareProgressTrack} aria-hidden>
            <div
              className={styles.prepareProgressFill}
              style={{ width: `${progress?.progress ?? 4}%` }}
            />
          </div>
          <div className={styles.prepareMetaRow}>
            <span>{elapsedLabel} elapsed</span>
            <span>{remainingLabel}</span>
          </div>
        </div>

        <div className={styles.prepareStepsPanel}>
          <ol className={styles.prepareSteps}>
            {STEP_ORDER.map((stepId, index) => {
              const active = !failed && progress?.step === stepId;
              const done = !failed && activeStepIndex > index;
              const label =
                stepId === 'generating_assets'
                  ? formatAssetStepLabel(stepId, active || done ? assetTypes : undefined)
                  : PREPARE_STEP_LABELS[stepId].label;
              const estimate = PREPARE_STEP_LABELS[stepId].estimate;

              return (
                <li
                  key={stepId}
                  className={`${styles.prepareStep}${active ? ` ${styles.prepareStepActive}` : ''}${done ? ` ${styles.prepareStepDone}` : ''}`}
                >
                  <span className={styles.prepareStepIcon} aria-hidden>
                    {done ? (
                      <Check className="w-4 h-4" strokeWidth={2.25} />
                    ) : active ? (
                      <Loader2 className={`w-4 h-4 ${styles.spinner}`} strokeWidth={1.75} />
                    ) : (
                      <span className={styles.prepareStepDot} />
                    )}
                  </span>
                  <span className={styles.prepareStepText}>
                    <span className={styles.prepareStepLabel}>{label}</span>
                    {estimate ? <span className={styles.prepareStepEstimate}>{estimate}</span> : null}
                  </span>
                </li>
              );
            })}
          </ol>
        </div>

        {failed ? (
          <div className={styles.prepareError}>
            <div className={styles.prepareErrorHeader}>
              <AlertCircle className="w-4 h-4" strokeWidth={2} aria-hidden />
              <p>{errorMessage ?? 'We couldn&apos;t finish preparing this notebook.'}</p>
            </div>
            <div className={styles.prepareErrorActions}>
              <button
                type="button"
                className={styles.prepareRetryBtn}
                onClick={() => setRetryKey((k) => k + 1)}
              >
                Try again
              </button>
              <button type="button" className={styles.prepareCancelBtn} onClick={onCancel}>
                Cancel
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
