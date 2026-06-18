'use client';

import type { TutorScopeSettings } from '@/lib/tutor-ncert-source';

function subjectDisplayLabel(scope: TutorScopeSettings): string {
  const key = String(scope.subject_key ?? scope.subject_slug ?? 'science');
  const labels: Record<string, string> = {
    mathematics: 'Mathematics',
    science: 'Science',
    history: 'History',
    geography: 'Geography',
    'civics-polity': 'Civics',
    economics: 'Economics',
    social_science: 'Social Science',
  };
  return labels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function ConceptChip({ label }: { label: string }) {
  return (
    <span
      className="inline-flex max-w-[160px] shrink-0 truncate rounded-full border border-[var(--color-home-border)] bg-[var(--color-brand-surface)] px-2.5 py-0.5 text-[11px] font-medium text-[var(--color-brand-primary)]"
      title={label}
    >
      {label}
    </span>
  );
}

interface TutorNotebookHeaderProps {
  scope: TutorScopeSettings;
}

export function TutorNotebookHeader({ scope }: TutorNotebookHeaderProps) {
  const chapterNo = scope.chapter_no ?? null;
  const chapterTitle = String(scope.chapter_title ?? scope.chapter_name ?? '').trim();
  const scopedConcept = scope.concept?.trim() || null;
  const isAllConcepts = !scopedConcept;

  const subjectLabel = subjectDisplayLabel(scope);
  const chapterLine =
    chapterNo != null && chapterTitle
      ? `Ch. ${chapterNo} ${chapterTitle}`
      : chapterNo != null
        ? `Ch. ${chapterNo}`
        : chapterTitle;

  const primaryLine = [subjectLabel, chapterLine].filter(Boolean).join(' · ');

  return (
    <div className="flex items-center gap-2 min-w-0 flex-nowrap overflow-hidden">
      <span className="text-[15px] font-bold text-[var(--color-home-text)] truncate min-w-0">
        {primaryLine}
      </span>
      {isAllConcepts ? (
        <ConceptChip label="All concepts" />
      ) : (
        <ConceptChip label={scopedConcept} />
      )}
    </div>
  );
}
