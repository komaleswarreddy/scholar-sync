'use client';

import { BookOpen, ExternalLink, Pencil, Sparkles } from 'lucide-react';

export function LibraryBottomBanner() {
  return (
    <div className="library-bottom-banner mt-8">
      <div className="flex flex-col sm:flex-row sm:items-center gap-4 sm:gap-6">
        <div className="library-banner-icon flex-shrink-0" aria-hidden>
          <BookOpen className="w-6 h-6 text-[var(--color-brand-text)]" strokeWidth={1.5} />
          <Pencil className="w-3.5 h-3.5 text-[var(--color-brand-text)] absolute bottom-1 right-1" />
          <Sparkles className="w-3.5 h-3.5 text-[var(--color-brand-text)] absolute -top-0.5 -right-0.5" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[15px] font-bold text-[var(--color-brand-primary)] leading-snug">
            Notebooks are your AI-powered study spaces.
          </p>
          <p className="text-[14px] text-[var(--color-home-text-muted)] mt-1 leading-relaxed">
            Upload, chat, generate notes, quizzes, mind maps and track mastery — all in one
            place.
          </p>
        </div>
        <a
          href="#"
          className="flex items-center gap-1.5 text-[14px] font-semibold text-[var(--color-brand-text)] hover:underline flex-shrink-0 self-start sm:self-center"
        >
          How it works
          <ExternalLink className="w-4 h-4" />
        </a>
      </div>
    </div>
  );
}
