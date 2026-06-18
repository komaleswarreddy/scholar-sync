'use client';

import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { ExamMetaChips } from '@/components/teacher/exams/ExamMetaChips';
import type { ClassExamAnalytics } from '@/lib/teacher-exam-types';

interface ClassAnalyticsHeaderProps {
  analytics: ClassExamAnalytics;
}

export function ClassAnalyticsHeader({ analytics }: ClassAnalyticsHeaderProps) {
  return (
    <header className="teacher-analytics-header">
      <Link href="/teacher/exams" className="teacher-analytics-header__back">
        <ArrowLeft className="h-4 w-4" aria-hidden />
        Back to exams
      </Link>
      <h1 className="teacher-analytics-header__title">{analytics.examName}</h1>
      <p className="teacher-analytics-header__subtitle">Class analytics</p>
      <ExamMetaChips
        examName=""
        subject={analytics.subject}
        classNum={analytics.classNum}
        section={analytics.section}
        examDate={analytics.examDate}
        board={analytics.board}
      />
    </header>
  );
}
