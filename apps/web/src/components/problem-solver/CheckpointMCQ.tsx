'use client';

import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { useProblemSolverContext } from '@/contexts/ProblemSolverContext';
import type { ProblemSolverCheckpoint } from '@/types/problem-solver';
import { isValidCheckpoint } from '@/lib/problem-solver-utils';
import styles from '@/components/tutor/tutor-mode.module.css';

export function CheckpointMCQ({ checkpoint }: { checkpoint: ProblemSolverCheckpoint }) {
  const { submitCheckpoint } = useProblemSolverContext();
  const [selected, setSelected] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const options = checkpoint.options ?? [];

  if (!isValidCheckpoint({ ...checkpoint, options })) {
    return null;
  }

  const handleSubmit = async () => {
    if (!selected) return;
    setIsSubmitting(true);
    try {
      await submitCheckpoint(checkpoint.number, selected);
      setSelected(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className={styles.psFlowSection}>
      <div className={styles.sectionHeader}>
        <span className={styles.stepBadge}>{checkpoint.number}</span>
        <h2 className={styles.sectionTitle}>Quick checkpoint</h2>
      </div>
      <p className={styles.psHint}>{checkpoint.prompt}</p>
      <div className={styles.psCheckpointOptions}>
        {options.map((option) => (
          <button
            key={option.id}
            type="button"
            className={`${styles.psCheckpointOption}${
              selected === option.id ? ` ${styles.psCheckpointOptionSelected}` : ''
            }`}
            onClick={() => setSelected(option.id)}
            disabled={isSubmitting}
          >
            <span className={styles.psCheckpointId}>{option.id}</span>
            <span>{option.label}</span>
          </button>
        ))}
      </div>
      <button
        type="button"
        className={styles.createBtn}
        disabled={!selected || isSubmitting}
        onClick={() => void handleSubmit()}
      >
        {isSubmitting ? (
          <>
            <Loader2 className={`w-4 h-4 ${styles.spinner}`} />
            Checking…
          </>
        ) : (
          'Continue'
        )}
      </button>
    </section>
  );
}
