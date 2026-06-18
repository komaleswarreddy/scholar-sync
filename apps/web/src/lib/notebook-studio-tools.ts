import type { LucideIcon } from 'lucide-react';
import {
  FileQuestion,
  Layers,
  Network,
  Presentation,
} from 'lucide-react';
import type { NotebookIconTone } from './notebook-ui-tokens';

export type NotebookStudioTool = {
  type: string;
  title: string;
  icon: LucideIcon;
  tone: NotebookIconTone;
};

export const NOTEBOOK_STUDIO_TOOL_TONES: Record<string, NotebookIconTone> = {
  mind_map: 'orange',
  flashcards: 'green',
  quiz: 'green',
  slide_deck: 'blue',
};

export const NOTEBOOK_STUDIO_TOOLS: NotebookStudioTool[] = [
  { type: 'mind_map', title: 'Mind Map', icon: Network, tone: 'orange' },
  { type: 'flashcards', title: 'Flashcards', icon: Layers, tone: 'green' },
  { type: 'quiz', title: 'Quiz', icon: FileQuestion, tone: 'green' },
  { type: 'slide_deck', title: 'Slide Deck', icon: Presentation, tone: 'blue' },
];

/** Tutor notebook studio — Flashcards first. */
export const TUTOR_NOTEBOOK_STUDIO_TOOLS: NotebookStudioTool[] = [
  { type: 'flashcards', title: 'Flashcards', icon: Layers, tone: 'green' },
  { type: 'quiz', title: 'Quiz', icon: FileQuestion, tone: 'green' },
  { type: 'mind_map', title: 'Mind Map', icon: Network, tone: 'orange' },
  { type: 'slide_deck', title: 'Slide Deck', icon: Presentation, tone: 'blue' },
];

/** Always visible in collapsed tutor studio sidebar. */
export const TUTOR_STUDIO_PRIMARY_TYPES = ['flashcards', 'quiz'];

/** Shown after "View all" in tutor studio sidebar. */
export const TUTOR_STUDIO_SECONDARY_TYPES = ['mind_map', 'slide_deck'];

/** Problem solver studio — Flashcards, Quiz, Mind Map only (no slide deck). */
export const PROBLEM_SOLVER_NOTEBOOK_STUDIO_TOOLS: NotebookStudioTool[] = [
  { type: 'flashcards', title: 'Flashcards', icon: Layers, tone: 'green' },
  { type: 'quiz', title: 'Quiz', icon: FileQuestion, tone: 'green' },
  { type: 'mind_map', title: 'Mind Map', icon: Network, tone: 'orange' },
];

export const PROBLEM_SOLVER_STUDIO_PRIMARY_TYPES = ['flashcards', 'quiz'];
export const PROBLEM_SOLVER_STUDIO_SECONDARY_TYPES = ['mind_map'];

/** Selection popover tools for problem solver chat. */
export const PROBLEM_SOLVER_SELECTION_STUDIO_TOOLS = PROBLEM_SOLVER_NOTEBOOK_STUDIO_TOOLS;

const TUTOR_TOOL_BY_TYPE = new Map(TUTOR_NOTEBOOK_STUDIO_TOOLS.map((tool) => [tool.type, tool]));

export type TutorStudioRecommendationInput = {
  type: string;
  reason?: string;
  auto_generate?: boolean;
};

const TUTOR_AUTO_GEN_ORDER = ['flashcards', 'quiz', 'mind_map', 'slide_deck'];

/** Top 2 studio types flagged for silent auto-generation (UI always shows all 4 cards). */
export function getTutorAutoGenerateTypes(
  recommendations?: TutorStudioRecommendationInput[] | null,
): string[] {
  if (!recommendations?.length) {
    return ['flashcards', 'quiz'];
  }
  const flagged = recommendations
    .filter((r) => r.auto_generate && TUTOR_TOOL_BY_TYPE.has(r.type))
    .map((r) => r.type);
  const ordered = TUTOR_AUTO_GEN_ORDER.filter((t) => flagged.includes(t));
  if (ordered.length >= 2) {
    return ordered.slice(0, 2);
  }
  const fallback = TUTOR_AUTO_GEN_ORDER.filter((t) => TUTOR_TOOL_BY_TYPE.has(t));
  return [...new Set([...ordered, ...fallback])].slice(0, 2);
}
