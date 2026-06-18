'use client';

import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { useProblemSolverContext } from '@/contexts/ProblemSolverContext';
import { SOLVING_MODE_OPTIONS, type SolvingMode } from '@/types/problem-solver';
import styles from '@/components/tutor/tutor-mode.module.css';

export function SolvingModeSelector() {
  const { selectMode, isStreaming, session } = useProblemSolverContext();
  const [pendingMode, setPendingMode] = useState<SolvingMode | null>(null);

  const handleSelect = async (mode: SolvingMode) => {
    if (isStreaming || pendingMode) return;
    setPendingMode(mode);
    try {
      await selectMode(mode);
    } finally {
      setPendingMode(null);
    }
  };

  return (
    <section className={styles.psFlowSection}>
      <div className={styles.sectionHeader}>
        <span className={styles.stepBadge}>3</span>
        <h2 className={styles.sectionTitle}>Choose how you want help</h2>
      </div>
      <div className={styles.psModeGrid}>
        {SOLVING_MODE_OPTIONS.map((mode) => {
          const isSelected = session?.solving_mode === mode.id;
          const isPending = pendingMode === mode.id;
          return (
            <button
              key={mode.id}
              type="button"
              className={`${styles.psModeCard}${isSelected ? ` ${styles.psModeCardSelected}` : ''}`}
              onClick={() => void handleSelect(mode.id)}
              disabled={Boolean(isStreaming || pendingMode)}
            >
              {mode.recommended ? (
                <span className={styles.psRecommendedTag}>Recommended for learning</span>
              ) : null}
              <p className={styles.psModeTitle}>{mode.title}</p>
              <p className={styles.psModeDesc}>{mode.description}</p>
              {isPending ? (
                <Loader2 className={`w-4 h-4 ${styles.spinner} mt-2`} strokeWidth={1.75} />
              ) : null}
            </button>
          );
        })}
      </div>
    </section>
  );
}
