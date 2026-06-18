'use client';

import Link from 'next/link';
import type { ClassExamAnalytics } from '@/lib/teacher-exam-types';
import { ClassAnalyticsHeader } from './ClassAnalyticsHeader';
import { ClassAnalyticsKpis } from './ClassAnalyticsKpis';
import { QuestionPerformanceTable } from './QuestionPerformanceTable';
import { WeakConceptsSection } from './WeakConceptsSection';

interface ClassAnalyticsPageProps {
  analytics: ClassExamAnalytics;
}

export function ClassAnalyticsPage({ analytics }: ClassAnalyticsPageProps) {
  return (
    <div className="teacher-exam-page teacher-analytics-page">
      <ClassAnalyticsHeader analytics={analytics} />
      <ClassAnalyticsKpis analytics={analytics} />
      <QuestionPerformanceTable questions={analytics.questions} />
      <WeakConceptsSection weakConcepts={analytics.weakConcepts} />

      <footer className="teacher-analytics-footer">
        <Link href="/teacher/exams" className="teacher-exam-success__btn teacher-exam-success__btn--secondary">
          Back to exams list
        </Link>
        <Link
          href={`/teacher/exams/new?examId=${analytics.examId}&view=graded`}
          className="teacher-exam-success__btn teacher-exam-success__btn--primary"
        >
          View graded summary
        </Link>
      </footer>
    </div>
  );
}
