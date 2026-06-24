/**
 * Exploratory notebooks (and dashboard chat) require uploaded sources for Studio.
 * Tutor / problem_solver notebooks use NCERT scope or other bootstrap paths.
 */

export type NotebookModeLike = 'exploratory' | 'tutor' | 'problem_solver' | string | undefined;

export function notebookModeRequiresUploadedSources(mode: NotebookModeLike): boolean {
  return mode !== 'tutor' && mode !== 'problem_solver';
}

export const EXPLORATORY_STUDIO_NO_SOURCES_MESSAGE =
  'Select at least one source to enable Studio tools.';

export const EXPLORATORY_STUDIO_SELECTION_BLOCKED_MESSAGE =
  'Upload and select at least one source before generating Studio content from chat.';
