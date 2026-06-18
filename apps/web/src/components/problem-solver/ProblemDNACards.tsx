'use client';

import type { ProblemSolverDna } from '@/types/problem-solver';
import styles from '@/components/tutor/tutor-mode.module.css';

export function ProblemDNACards({
  dna,
  compact = false,
}: {
  dna: ProblemSolverDna;
  compact?: boolean;
}) {
  const concepts = dna.concepts ?? dna.conceptTags ?? [];
  const estimatedMinutes = dna.estimated_minutes ?? dna.expectedTimeMinutes;

  if (compact) {
    return (
      <div className={styles.psDnaCompact}>
        {dna.subject ? <span className={styles.psDnaChip}>{dna.subject}</span> : null}
        {dna.chapter ? <span className={styles.psDnaChip}>{dna.chapter}</span> : null}
        {dna.difficulty ? <span className={styles.psDnaChip}>{dna.difficulty}</span> : null}
        {estimatedMinutes != null ? (
          <span className={styles.psDnaChip}>{estimatedMinutes} min</span>
        ) : null}
      </div>
    );
  }

  return (
    <section className={styles.psFlowSection}>
      <div className={styles.sectionHeader}>
        <span className={styles.stepBadge}>2</span>
        <h2 className={styles.sectionTitle}>Problem DNA</h2>
      </div>
      <div className={styles.psDnaGrid}>
        <DnaCard label="Subject" value={dna.subject ?? '—'} />
        <DnaCard label="Chapter" value={dna.chapter ?? '—'} />
        <DnaCard label="Difficulty" value={dna.difficulty ?? '—'} />
        <DnaCard
          label="Est. time"
          value={
            estimatedMinutes != null ? `${estimatedMinutes} min` : '—'
          }
        />
        <DnaCard label="Confidence" value={dna.confidence ?? '—'} />
      </div>
      {concepts.length > 0 ? (
        <div className={styles.psConceptList}>
          <p className={styles.psConceptLabel}>Key concepts</p>
          <div className={styles.psConceptPills}>
            {concepts.map((concept) => (
              <span key={concept} className={styles.psConceptPill}>
                {concept}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

function DnaCard({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.psDnaCard}>
      <p className={styles.psDnaLabel}>{label}</p>
      <p className={styles.psDnaValue}>{value}</p>
    </div>
  );
}
