'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { ClassAnalyticsPage } from '@/components/teacher/analytics/ClassAnalyticsPage';
import { buildClassExamAnalytics } from '@/lib/teacher-exam-analytics-mock-data';
import { getExamById } from '@/lib/teacher-exam-storage';
import type { ClassExamAnalytics, TeacherExam } from '@/lib/teacher-exam-types';

type PageState =
  | { kind: 'loading' }
  | { kind: 'not_found' }
  | { kind: 'draft'; exam: TeacherExam }
  | { kind: 'ready'; analytics: ClassExamAnalytics };

export default function TeacherExamAnalyticsPage() {
  const params = useParams();
  const router = useRouter();
  const examId = typeof params.examId === 'string' ? params.examId : '';
  const [state, setState] = useState<PageState>({ kind: 'loading' });

  useEffect(() => {
    if (!examId) {
      router.replace('/teacher/exams');
      return;
    }

    const exam = getExamById(examId);
    if (!exam) {
      setState({ kind: 'not_found' });
      return;
    }

    if (exam.status === 'draft') {
      setState({ kind: 'draft', exam });
      return;
    }

    if (exam.status === 'graded' || exam.status === 'archived') {
      setState({ kind: 'ready', analytics: buildClassExamAnalytics(exam) });
      return;
    }

    setState({ kind: 'not_found' });
  }, [examId, router]);

  if (state.kind === 'loading') {
    return (
      <div className="teacher-exam-page teacher-analytics-page">
        <p className="teacher-analytics-loading">Loading analytics…</p>
      </div>
    );
  }

  if (state.kind === 'not_found') {
    return (
      <div className="teacher-exam-page teacher-analytics-page">
        <div className="teacher-analytics-empty">
          <h2 className="teacher-analytics-empty__title">Exam not found</h2>
          <p className="teacher-analytics-empty__desc">
            This exam may have been removed or the link is invalid.
          </p>
          <Link href="/teacher/exams" className="teacher-exam-success__btn teacher-exam-success__btn--primary">
            Back to exams list
          </Link>
        </div>
      </div>
    );
  }

  if (state.kind === 'draft') {
    return (
      <div className="teacher-exam-page teacher-analytics-page">
        <div className="teacher-analytics-empty">
          <h2 className="teacher-analytics-empty__title">Complete grading first</h2>
          <p className="teacher-analytics-empty__desc">
            {state.exam.examName || 'This exam'} is still a draft. Finish the wizard and grade OMR
            sheets to view class analytics.
          </p>
          <Link
            href={`/teacher/exams/new?examId=${state.exam.id}`}
            className="teacher-exam-success__btn teacher-exam-success__btn--primary"
          >
            Resume exam setup
          </Link>
        </div>
      </div>
    );
  }

  return <ClassAnalyticsPage analytics={state.analytics} />;
}
