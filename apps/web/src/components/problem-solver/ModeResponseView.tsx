'use client';



import { Loader2 } from 'lucide-react';

import { RichMarkdown } from '@/components/common/RichMarkdown';

import type { ProblemSolverSection } from '@/types/problem-solver';

import styles from '@/components/tutor/tutor-mode.module.css';



export function ModeResponseView({

  title,

  sections,

  isStreaming,

  finalAnswer,

  statusMessage,

}: {

  title?: string;

  sections: ProblemSolverSection[];

  isStreaming?: boolean;

  finalAnswer?: string | null;

  statusMessage?: string | null;

}) {

  if (!sections.length && !isStreaming) return null;



  return (

    <section className={styles.psFlowSection}>

      <div className={styles.sectionHeader}>

        <span className={styles.stepBadge}>4</span>

        <h2 className={styles.sectionTitle}>{title || 'Guided response'}</h2>

        {isStreaming ? (

          <Loader2 className={`w-4 h-4 ${styles.spinner} ml-auto`} strokeWidth={1.75} />

        ) : null}

      </div>

      {isStreaming && !sections.length && statusMessage ? (

        <p className={styles.psHint}>{statusMessage}</p>

      ) : null}

      <div className={styles.psResponseBody}>

        {sections.map((section, idx) => (

          <article key={`${section.heading}-${idx}`} className={styles.psResponseSection}>

            <h3 className={styles.psResponseHeading}>{section.heading}</h3>

            <div className={styles.psResponseContent}>

              <RichMarkdown content={section.bodyMarkdown} variant="problem-solver" />

            </div>

          </article>

        ))}

        {finalAnswer ? (

          <div className={styles.psFinalAnswer}>

            <p className={styles.psDnaLabel}>Final answer</p>

            <div className={styles.psDnaValue}>

              <RichMarkdown content={finalAnswer} variant="problem-solver" />

            </div>

          </div>

        ) : null}

      </div>

    </section>

  );

}

