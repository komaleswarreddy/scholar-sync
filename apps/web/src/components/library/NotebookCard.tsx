'use client';

import { Clock, FileText, HelpCircle, Layers, Lightbulb, MoreVertical } from 'lucide-react';
import { MasteryRing } from './MasteryRing';
import { getSubjectTheme, type LibraryNotebook } from '@/lib/library-mock-data';

type NotebookCardProps = {
  notebook: LibraryNotebook;
  onOpen?: (id: string) => void;
};

export function NotebookCard({ notebook, onOpen }: NotebookCardProps) {
  const theme = getSubjectTheme(notebook.subject);

  return (
    <article className="library-notebook-card group">
      <div className="flex items-start justify-between gap-2">
        <p
          className="text-[11px] font-bold tracking-wide uppercase"
          style={{ color: theme.label }}
        >
          {notebook.subject} • {notebook.classLevel}
        </p>
        <div className="flex items-center gap-2 flex-shrink-0">
          {notebook.mode === 'problem_solver' ? (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide bg-[#edf7f2] text-[#21594f]">
              <Lightbulb className="w-3 h-3" strokeWidth={1.75} />
              Problem Solver
            </span>
          ) : null}
          <div className="flex items-center gap-1.5">
            <MasteryRing percent={notebook.masteryPercent} strokeColor={theme.ring} />
            <span className="text-[11px] font-semibold text-[var(--color-home-text-muted)] whitespace-nowrap">
              {notebook.masteryPercent}% mastery
            </span>
          </div>
          <button
            type="button"
            className="p-1 rounded-md text-[var(--color-home-label)] hover:text-[var(--color-home-text)] hover:bg-[var(--color-brand-surface)] transition-colors"
            aria-label="Notebook options"
          >
            <MoreVertical className="w-4 h-4" />
          </button>
        </div>
      </div>

      <button
        type="button"
        onClick={() => onOpen?.(notebook.id)}
        className="text-left w-full mt-3"
      >
        <h3 className="text-[17px] font-bold text-[var(--color-home-text)] leading-snug group-hover:text-[var(--color-brand-text)] transition-colors">
          {notebook.title}
        </h3>
        <p className="text-[13px] text-[var(--color-home-text-muted)] mt-1 leading-snug">
          {notebook.subtitle}
        </p>
        <p className="text-[13px] mt-2.5 leading-snug">
          <span className="font-bold text-[var(--color-brand-text)]">Focus:</span>{' '}
          <span className="text-[var(--color-home-text-muted)]">{notebook.focus}</span>
        </p>
      </button>

      <div className="flex items-center gap-4 mt-4 text-[12px] text-[var(--color-home-text-muted)]">
        <span className="flex items-center gap-1.5">
          <FileText className="w-3.5 h-3.5" strokeWidth={1.75} />
          {notebook.sources} sources
        </span>
        <span className="flex items-center gap-1.5">
          <Layers className="w-3.5 h-3.5" strokeWidth={1.75} />
          {notebook.studyAssets} study assets
        </span>
        <span className="flex items-center gap-1.5">
          <HelpCircle className="w-3.5 h-3.5" strokeWidth={1.75} />
          {notebook.quizzes} {notebook.quizzes === 1 ? 'quiz' : 'quizzes'}
        </span>
      </div>

      <div className="border-t border-[var(--color-home-border)] mt-4 pt-3">
        <p className="flex items-center gap-1.5 text-[12px] text-[var(--color-home-text-muted)]">
          <Clock className="w-3.5 h-3.5" strokeWidth={1.75} />
          Last studied: {notebook.lastStudied}
        </p>
      </div>
    </article>
  );
}
