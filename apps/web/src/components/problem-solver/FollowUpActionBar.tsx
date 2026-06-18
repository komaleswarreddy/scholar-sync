'use client';

import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { useProblemSolverContext } from '@/contexts/ProblemSolverContext';
import type { ProblemSolverFollowUpButton } from '@/types/problem-solver';
import styles from '@/components/tutor/tutor-mode.module.css';

export function FollowUpActionBar({
  buttons,
}: {
  buttons: ProblemSolverFollowUpButton[];
}) {
  const { triggerFollowUp, isFollowUpLoading, streamError } = useProblemSolverContext();
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [customInput, setCustomInput] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);

  if (!buttons.length) return null;

  const busy = isFollowUpLoading || Boolean(pendingAction);
  const displayError = localError || streamError;

  const handleAction = async (action: string) => {
    setPendingAction(action);
    setLocalError(null);
    try {
      await triggerFollowUp(action, customInput.trim() || undefined);
      setCustomInput('');
    } catch {
      setLocalError('Could not complete that follow-up. Please try again.');
    } finally {
      setPendingAction(null);
    }
  };

  const handleCustomSubmit = () => {
    const text = customInput.trim();
    if (!text || busy) return;
    void handleAction('CUSTOM_FOLLOW_UP');
  };

  return (
    <section className={styles.psFlowSection}>
      <div className={styles.sectionHeader}>
        <span className={styles.stepBadge}>5</span>
        <h2 className={styles.sectionTitle}>What next?</h2>
        {busy ? (
          <Loader2 className={`w-4 h-4 ${styles.spinner} ml-auto`} strokeWidth={1.75} />
        ) : null}
      </div>
      <div className={styles.psFollowUpPills}>
        {buttons.map((btn) => (
          <button
            key={btn.action}
            type="button"
            className={styles.psFollowUpPill}
            disabled={busy}
            onClick={() => void handleAction(btn.action)}
          >
            {pendingAction === btn.action ? (
              <Loader2 className={`w-3.5 h-3.5 ${styles.spinner}`} strokeWidth={1.75} />
            ) : null}
            {btn.label}
          </button>
        ))}
      </div>
      <input
        type="text"
        className={styles.psFollowUpInput}
        placeholder="Optional: add a follow-up question…"
        value={customInput}
        onChange={(e) => setCustomInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            handleCustomSubmit();
          }
        }}
        disabled={busy}
      />
      {displayError ? <p className={styles.psError}>{displayError}</p> : null}
    </section>
  );
}
