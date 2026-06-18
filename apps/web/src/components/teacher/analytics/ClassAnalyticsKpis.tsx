'use client';

import type { ClassExamAnalytics } from '@/lib/teacher-exam-types';

interface ClassAnalyticsKpisProps {
  analytics: ClassExamAnalytics;
}

export function ClassAnalyticsKpis({ analytics }: ClassAnalyticsKpisProps) {
  const { summary } = analytics;

  return (
    <div className="teacher-exam-stat-grid teacher-analytics-kpis">
      <div className="teacher-exam-stat-grid__item">
        <span className="teacher-exam-stat-grid__value">{summary.studentsGraded}</span>
        <span className="teacher-exam-stat-grid__label">Students graded</span>
      </div>
      <div className="teacher-exam-stat-grid__item">
        <span className="teacher-exam-stat-grid__value">
          {summary.averageScore}/{summary.maxScore}
        </span>
        <span className="teacher-exam-stat-grid__label">Average score</span>
      </div>
      <div className="teacher-exam-stat-grid__item">
        <span className="teacher-exam-stat-grid__value">{analytics.totalQuestions}</span>
        <span className="teacher-exam-stat-grid__label">Total questions</span>
      </div>
      <div className="teacher-exam-stat-grid__item">
        <span className="teacher-exam-stat-grid__value">{analytics.classCorrectPct}%</span>
        <span className="teacher-exam-stat-grid__label">Class correct rate</span>
      </div>
      <div className="teacher-exam-stat-grid__item">
        <span className="teacher-exam-stat-grid__value">{analytics.weakConcepts.length}</span>
        <span className="teacher-exam-stat-grid__label">Weak concepts</span>
      </div>
      <div className="teacher-exam-stat-grid__item">
        <span className="teacher-exam-stat-grid__value">{analytics.highestMissRatePct}%</span>
        <span className="teacher-exam-stat-grid__label">Highest miss rate</span>
      </div>
    </div>
  );
}
