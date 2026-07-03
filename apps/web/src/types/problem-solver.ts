export type SolvingMode =
  | 'EXPLAIN_FROM_BASICS'
  | 'HELP_ME_SOLVE_IT'
  | 'SHOW_MISSING_IDEA'
  | 'SHOW_BEST_APPROACH';

export type ProblemSolverFlowStep =
  | 'idle_intake'
  | 'extracting'
  | 'dna_loading'
  | 'dna_ready'
  | 'mode_select'
  | 'streaming_response'
  | 'checkpoint'
  | 'follow_up';

export type ProblemSolverSection = {
  heading: string;
  bodyMarkdown: string;
};

export type ProblemSolverCheckpoint = {
  number: number;
  prompt: string;
  options: Array<{ id: string; label: string }>;
};

export type ProblemSolverFollowUpButton = {
  label: string;
  action: string;
};

export type ProblemSolverModeResponse = {
  title?: string;
  mode?: SolvingMode;
  sections?: ProblemSolverSection[];
  checkpoint?: ProblemSolverCheckpoint | null;
  revealLevel?: string;
  followUpButtons?: ProblemSolverFollowUpButton[];
  finalAnswer?: string | null;
  interactionCount?: number;
  assistant_message_id?: string;
};

export type ProblemSolverDna = {
  subject?: string;
  chapter?: string;
  difficulty?: string;
  estimated_minutes?: number;
  expectedTimeMinutes?: number;
  concepts?: string[];
  conceptTags?: string[];
  confidence?: string;
  ncert_class?: number;
};

export type ProblemSolverSession = {
  session_id: string;
  notebook_id: string;
  state: string;
  problem_text?: string | null;
  problem_text_normalized?: string | null;
  input_type: string;
  source_refs: Array<Record<string, unknown>>;
  problem_dna?: ProblemSolverDna | null;
  solving_mode?: SolvingMode | null;
  interaction_count: number;
  last_response?: ProblemSolverModeResponse | null;
  assistant_message_id?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export const SOLVING_MODE_OPTIONS: Array<{
  id: SolvingMode;
  title: string;
  description: string;
  recommended?: boolean;
}> = [
  {
    id: 'EXPLAIN_FROM_BASICS',
    title: 'Explain from the Basics',
    description: 'Build understanding from first principles with NCERT-grounded steps.',
  },
  {
    id: 'HELP_ME_SOLVE_IT',
    title: 'Help Me Solve It',
    description: 'Guided hints with up to two quick checkpoints — no answer until you earn it.',
    recommended: true,
  },
  {
    id: 'SHOW_MISSING_IDEA',
    title: 'Show the Missing Idea',
    description: 'Identify the one concept blocking you and how to apply it.',
  },
  {
    id: 'SHOW_BEST_APPROACH',
    title: 'Show the Best Approach',
    description: 'See the efficient solution path with reasoning and takeaway.',
  },
];
