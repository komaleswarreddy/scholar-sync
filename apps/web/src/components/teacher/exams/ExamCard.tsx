'use client';

import { useRouter } from 'next/navigation';
import { Archive, Calendar, ChevronRight, Users } from 'lucide-react';
import { getRemainingStepLabel } from '@/lib/teacher-exam-types';
import type { TeacherExam } from '@/lib/teacher-exam-types';

interface ExamCardProps {
  exam: TeacherExam;
  tab: 'upcoming' | 'graded' | 'archived';
}

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

export function ExamCard({ exam, tab }: ExamCardProps) {
  const router = useRouter();
  const questionCount = exam.questions.length || 20;

  const handleResume = () => {
    router.push(`/teacher/exams/new?examId=${exam.id}`);
  };

  const handleViewAnalytics = () => {
    router.push(`/teacher/exams/${exam.id}/analytics`);
  };

  if (tab === 'archived') {
    return (
      <article className="teacher-exam-card teacher-exam-card--archived">
        <div className="teacher-exam-card__header">
          <span className="teacher-exam-card__status teacher-exam-card__status--archived">
            <Archive className="h-3.5 w-3.5" />
            Archived
          </span>
        </div>
        <h3 className="teacher-exam-card__title">{exam.examName}</h3>
        <p className="teacher-exam-card__meta">
          {exam.subject} · Class {exam.classNum}
          {exam.section ? ` · Section ${exam.section}` : ''}
        </p>
        <p className="teacher-exam-card__date">
          <Calendar className="h-3.5 w-3.5" />
          {formatDate(exam.examDate)}
        </p>
        {exam.archivedAt && (
          <p className="teacher-exam-card__archived-date">
            Archived on {formatDate(exam.archivedAt)}
          </p>
        )}
      </article>
    );
  }

  if (tab === 'graded') {
    const summary = exam.gradingSummary;
    return (
      <article className="teacher-exam-card">
        <div className="teacher-exam-card__header">
          <span className="teacher-exam-card__status teacher-exam-card__status--graded">Graded</span>
        </div>
        <h3 className="teacher-exam-card__title">{exam.examName}</h3>
        <p className="teacher-exam-card__meta">
          {exam.subject} · Class {exam.classNum}
          {exam.section ? ` · Section ${exam.section}` : ''}
        </p>
        <p className="teacher-exam-card__date">
          <Calendar className="h-3.5 w-3.5" />
          {formatDate(exam.examDate)}
        </p>
        {summary && (
          <div className="teacher-exam-stat-grid teacher-exam-stat-grid--inline">
            <div className="teacher-exam-stat-grid__item">
              <span className="teacher-exam-stat-grid__value">{summary.averageScore}</span>
              <span className="teacher-exam-stat-grid__label">Avg score</span>
            </div>
            <div className="teacher-exam-stat-grid__item">
              <span className="teacher-exam-stat-grid__value">{summary.studentsGraded}</span>
              <span className="teacher-exam-stat-grid__label">Students graded</span>
            </div>
            <div className="teacher-exam-stat-grid__item">
              <span className="teacher-exam-stat-grid__value">{summary.weakConcepts}</span>
              <span className="teacher-exam-stat-grid__label">Weak concepts</span>
            </div>
          </div>
        )}
        <button type="button" className="teacher-exam-card__cta" onClick={handleViewAnalytics}>
          View analytics
          <ChevronRight className="h-4 w-4" />
        </button>
      </article>
    );
  }

  return (
    <article className="teacher-exam-card">
      <div className="teacher-exam-card__header">
        <span className="teacher-exam-card__status teacher-exam-card__status--draft">Draft</span>
      </div>
      <h3 className="teacher-exam-card__title">{exam.examName || 'Untitled exam'}</h3>
      <p className="teacher-exam-card__meta">
        {exam.subject || 'Subject'} · Class {exam.classNum || '—'}
        {exam.section ? ` · Section ${exam.section}` : ''}
      </p>
      <p className="teacher-exam-card__date">
        <Calendar className="h-3.5 w-3.5" />
        {exam.examDate ? formatDate(exam.examDate) : 'Date not set'}
      </p>
      <p className="teacher-exam-card__questions">
        <Users className="h-3.5 w-3.5" />
        {questionCount} questions
      </p>
      <div className="teacher-exam-card__setup-panel">
        <p className="teacher-exam-card__setup-label">
          {getRemainingStepLabel(exam.wizardStep < 6 ? exam.wizardStep : 1)}
        </p>
        <button type="button" className="teacher-exam-card__setup-cta" onClick={handleResume}>
          Complete setup
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </article>
  );
}
