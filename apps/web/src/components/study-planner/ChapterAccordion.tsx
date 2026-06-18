'use client';

import { ChevronDown, ChevronUp } from 'lucide-react';
import type { ChapterOption } from '@/lib/study-planner-types';
import { SelectableChip } from './SelectableChip';

type ChapterAccordionProps = {
  subjectLabel: string;
  chapters: ChapterOption[];
  selectedChapterNos: number[];
  expanded: boolean;
  onToggleExpand: () => void;
  onToggleChapter: (chapterNo: number) => void;
};

export function ChapterAccordion({
  subjectLabel,
  chapters,
  selectedChapterNos,
  expanded,
  onToggleExpand,
  onToggleChapter,
}: ChapterAccordionProps) {
  const selectedCount = selectedChapterNos.length;
  const totalCount = chapters.length;

  return (
    <div className="study-plan-accordion">
      <button
        type="button"
        className="study-plan-accordion-header"
        onClick={onToggleExpand}
        aria-expanded={expanded}
      >
        <span>
          {subjectLabel} {selectedCount} / {totalCount} selected
        </span>
        {expanded ? (
          <ChevronUp className="w-4 h-4" strokeWidth={1.75} />
        ) : (
          <ChevronDown className="w-4 h-4" strokeWidth={1.75} />
        )}
      </button>
      {expanded && (
        <div className="study-plan-accordion-body">
          {chapters.map((chapter) => (
            <SelectableChip
              key={chapter.chapterNo}
              label={chapter.label}
              selected={selectedChapterNos.includes(chapter.chapterNo)}
              onClick={() => onToggleChapter(chapter.chapterNo)}
              variant="chapter"
            />
          ))}
        </div>
      )}
    </div>
  );
}
