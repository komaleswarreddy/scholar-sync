'use client';

import { AlertTriangle, Lightbulb } from 'lucide-react';
import type { WeakConceptAnalytics } from '@/lib/teacher-exam-types';

interface WeakConceptsSectionProps {
  weakConcepts: WeakConceptAnalytics[];
}

function formatQuestionList(numbers: number[]): string {
  if (numbers.length === 0) return '—';
  return numbers.map((n) => `Q${n}`).join(', ');
}

export function WeakConceptsSection({ weakConcepts }: WeakConceptsSectionProps) {
  if (weakConcepts.length === 0) {
    return (
      <section className="teacher-analytics-section teacher-analytics-section--positive">
        <h2 className="teacher-analytics-section__title">Weak concepts</h2>
        <p className="teacher-analytics-section__desc">
          No concepts below 60% — strong class performance across all mapped topics.
        </p>
      </section>
    );
  }

  return (
    <section className="teacher-analytics-weak-section">
      <div className="teacher-analytics-section__header-row">
        <h2 className="teacher-analytics-section__title">Weak concepts &amp; suggestions</h2>
        <span className="teacher-analytics-weak-badge">
          <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
          {weakConcepts.length} below 60%
        </span>
      </div>
      <p className="teacher-analytics-section__desc">
        Concepts where the class average correct rate is under 60%, with recommended teaching actions.
      </p>

      <div className="teacher-analytics-weak-grid">
        <div className="teacher-analytics-weak-list">
          {weakConcepts.map((concept) => (
            <article key={concept.conceptId} className="teacher-analytics-weak-card">
              <h3 className="teacher-analytics-weak-card__title">{concept.title}</h3>
              <p className="teacher-analytics-weak-card__path">{concept.path}</p>
              <div className="teacher-analytics-weak-card__stats">
                <span className="teacher-analytics-weak-card__pct">{concept.classCorrectPct}%</span>
                <span className="teacher-analytics-weak-card__label">class correct</span>
              </div>
              <div className="teacher-analytics-bar teacher-analytics-bar--compact">
                <div
                  className="teacher-analytics-bar__fill teacher-analytics-bar__fill--weak"
                  style={{ width: `${concept.classCorrectPct}%` }}
                />
              </div>
              <p className="teacher-analytics-weak-card__questions">
                Affected: {formatQuestionList(concept.affectedQuestionNumbers)}
              </p>
            </article>
          ))}
        </div>

        <div className="teacher-analytics-suggestions">
          {weakConcepts.map((concept) => (
            <article key={`sug-${concept.conceptId}`} className="teacher-analytics-suggestion-card">
              <h3 className="teacher-analytics-suggestion-card__title">
                <Lightbulb className="h-4 w-4" aria-hidden />
                Suggestions for {concept.title}
              </h3>
              <ul className="teacher-analytics-suggestion-card__list">
                {concept.suggestions.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
