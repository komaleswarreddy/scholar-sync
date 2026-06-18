import type {
  ProblemSolverCheckpoint,
  ProblemSolverFollowUpButton,
  ProblemSolverModeResponse,
  ProblemSolverSection,
} from '@/types/problem-solver';

export function isValidCheckpoint(
  checkpoint: ProblemSolverCheckpoint | null | undefined,
): checkpoint is ProblemSolverCheckpoint {
  return Boolean(
    checkpoint &&
      typeof checkpoint.prompt === 'string' &&
      checkpoint.prompt.trim().length > 0 &&
      Array.isArray(checkpoint.options) &&
      checkpoint.options.length > 0 &&
      checkpoint.options.every(
        (opt) => opt && typeof opt.id === 'string' && typeof opt.label === 'string',
      ),
  );
}

export function normalizeCheckpoint(
  checkpoint: Partial<ProblemSolverCheckpoint> | null | undefined,
  checkpointNumber = 1,
): ProblemSolverCheckpoint | null {
  if (!checkpoint) return null;
  const prompt =
    typeof checkpoint.prompt === 'string' && checkpoint.prompt.trim()
      ? checkpoint.prompt.trim()
      : checkpointNumber > 1
        ? 'Which equation should we use next?'
        : 'Which idea should we use first?';
  const number = checkpoint.number ?? checkpointNumber;
  const options = Array.isArray(checkpoint.options)
    ? checkpoint.options.filter(
        (opt): opt is { id: string; label: string } =>
          Boolean(opt?.id && opt?.label),
      )
    : [];
  if (!options.length) return null;
  return { number, prompt, options };
}

type SectionLike = {
  heading?: string;
  bodyMarkdown?: string;
  body?: string;
};

export function normalizeResponseSections(
  sections: SectionLike[] | null | undefined,
): ProblemSolverSection[] {
  if (!Array.isArray(sections)) return [];
  return sections
    .filter((s): s is SectionLike => Boolean(s && typeof s === 'object'))
    .map((s) => ({
      heading: String(s.heading || 'Section'),
      bodyMarkdown: String(s.bodyMarkdown ?? s.body ?? ''),
    }))
    .filter((s) => s.heading || s.bodyMarkdown);
}

export function normalizeFollowUpButtons(
  buttons: Array<Record<string, unknown>> | null | undefined,
): ProblemSolverFollowUpButton[] {
  if (!Array.isArray(buttons)) return [];
  const out: ProblemSolverFollowUpButton[] = [];
  for (const btn of buttons) {
    if (!btn || typeof btn !== 'object') continue;
    const action = String(btn.action ?? btn.id ?? '');
    const label = String(btn.label ?? btn.text ?? action);
    if (action) out.push({ label, action });
  }
  return out;
}

export function applyModeResponseToView(
  response: ProblemSolverModeResponse | null | undefined,
): { title: string; sections: ProblemSolverSection[] } {
  if (!response) return { title: '', sections: [] };
  return {
    title: response.title ?? '',
    sections: normalizeResponseSections(response.sections),
  };
}
