'use client';

import { Calendar, GraduationCap } from 'lucide-react';
import type { ExamBoard } from '@/lib/teacher-exam-types';

interface ExamMetaChipsProps {
  examName: string;
  subject: string;
  classNum: number | null;
  section: string;
  examDate: string;
  board: ExamBoard;
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '—';
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

export function ExamMetaChips({
  examName,
  subject,
  classNum,
  section,
  examDate,
  board,
}: ExamMetaChipsProps) {
  const classSection = [
    subject || 'Subject',
    classNum ? `Class ${classNum}` : null,
    section ? `Section ${section}` : null,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <div className="teacher-exam-meta-chips">
      {examName && (
        <span className="teacher-exam-meta-chips__chip teacher-exam-meta-chips__chip--name">
          {examName}
        </span>
      )}
      <span className="teacher-exam-meta-chips__chip">
        <GraduationCap className="h-3.5 w-3.5" />
        {classSection}
      </span>
      {examDate && (
        <span className="teacher-exam-meta-chips__chip">
          <Calendar className="h-3.5 w-3.5" />
          {formatDate(examDate)}
        </span>
      )}
      <span className="teacher-exam-meta-chips__chip teacher-exam-meta-chips__chip--board">
        {board}
      </span>
    </div>
  );
}
