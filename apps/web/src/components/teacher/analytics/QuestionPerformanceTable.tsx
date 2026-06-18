'use client';

import type { QuestionAnalyticsRow } from '@/lib/teacher-exam-types';

interface QuestionPerformanceTableProps {
  questions: QuestionAnalyticsRow[];
}

function PctBar({
  value,
  variant,
}: {
  value: number;
  variant: 'correct' | 'wrong' | 'unanswered';
}) {
  const displayWidth = value > 0 ? Math.max(value, 6) : 0;

  return (
    <div className={`teacher-analytics-pct teacher-analytics-pct--${variant}`}>
      <div className="teacher-analytics-pct__track">
        <div
          className="teacher-analytics-pct__fill"
          style={{ width: `${displayWidth}%` }}
        />
      </div>
      <span className="teacher-analytics-pct__value">{value}%</span>
    </div>
  );
}

export function QuestionPerformanceTable({ questions }: QuestionPerformanceTableProps) {
  return (
    <section className="teacher-analytics-section teacher-analytics-section--table">
      <div className="teacher-analytics-section__header-row">
        <div>
          <h2 className="teacher-analytics-section__title">Question performance</h2>
          <p className="teacher-analytics-section__desc teacher-analytics-section__desc--flush">
            Sorted by lowest correct rate. Shows how the class answered each question.
          </p>
        </div>
        <div className="teacher-analytics-legend" aria-hidden>
          <span className="teacher-analytics-legend__item teacher-analytics-legend__item--correct">
            Correct
          </span>
          <span className="teacher-analytics-legend__item teacher-analytics-legend__item--wrong">
            Wrong
          </span>
          <span className="teacher-analytics-legend__item teacher-analytics-legend__item--unanswered">
            Unanswered
          </span>
        </div>
      </div>

      <div className="teacher-analytics-table-wrap">
        <table className="teacher-analytics-table">
          <thead>
            <tr>
              <th className="teacher-analytics-table__th-q">Q#</th>
              <th className="teacher-analytics-table__th-concept">Concept</th>
              <th className="teacher-analytics-table__th-answer">Correct</th>
              <th className="teacher-analytics-table__th-pct teacher-analytics-table__th-pct--correct">
                Correct %
              </th>
              <th className="teacher-analytics-table__th-pct teacher-analytics-table__th-pct--wrong">
                Wrong %
              </th>
              <th className="teacher-analytics-table__th-pct teacher-analytics-table__th-pct--unanswered">
                Unanswered %
              </th>
            </tr>
          </thead>
          <tbody>
            {questions.map((q) => (
              <tr key={q.questionId}>
                <td className="teacher-analytics-table__qnum">
                  <span className="teacher-analytics-table__qnum-badge">Q{q.number}</span>
                </td>
                <td className="teacher-analytics-table__concept-cell">
                  <span className="teacher-analytics-table__concept">{q.conceptTitle}</span>
                  <span className="teacher-analytics-table__path">{q.conceptPath}</span>
                </td>
                <td className="teacher-analytics-table__answer-cell">
                  <span className="teacher-analytics-table__answer-badge">{q.correctAnswer}</span>
                </td>
                <td className="teacher-analytics-table__pct-cell">
                  <PctBar value={q.pctCorrect} variant="correct" />
                </td>
                <td className="teacher-analytics-table__pct-cell">
                  <PctBar value={q.pctWrong} variant="wrong" />
                </td>
                <td className="teacher-analytics-table__pct-cell">
                  <PctBar value={q.pctUnanswered} variant="unanswered" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
