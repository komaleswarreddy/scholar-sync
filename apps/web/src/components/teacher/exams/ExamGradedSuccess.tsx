'use client';

import Link from 'next/link';
import { CheckCircle2 } from 'lucide-react';
import type { ExamGradingSummary } from '@/lib/teacher-exam-types';

interface ExamGradedSuccessProps {
  examId: string;
  examName: string;
  summary: ExamGradingSummary;
}

export function ExamGradedSuccess({ examId, examName, summary }: ExamGradedSuccessProps) {
  return (
    <div className="teacher-exam-success">
      <div className="teacher-exam-success__icon-wrap">
        <CheckCircle2 className="h-12 w-12 teacher-exam-success__icon" />
      </div>
      <h2 className="teacher-exam-success__title">Exam graded</h2>
      <p className="teacher-exam-success__subtitle">
        {examName} has been graded successfully.
      </p>

      <div className="teacher-exam-stat-grid">
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
          <span className="teacher-exam-stat-grid__value">{summary.weakConcepts}</span>
          <span className="teacher-exam-stat-grid__label">Weak concepts</span>
        </div>
      </div>

      <div className="teacher-exam-success__actions">
        <Link href="/teacher/exams" className="teacher-exam-success__btn teacher-exam-success__btn--secondary">
          Back to exams list
        </Link>
        <Link
          href={`/teacher/exams/${examId}/analytics`}
          className="teacher-exam-success__btn teacher-exam-success__btn--primary"
        >
          View class analytics
        </Link>
      </div>
    </div>
  );
}
