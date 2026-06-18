import type { LibraryNotebook } from '@/lib/library-mock-data';

export type ApiNotebookListItem = {
  id: string;
  title: string;
  slug: string;
  subtitle?: string | null;
  subject?: string | null;
  class_level?: string | null;
  focus?: string | null;
  mastery_percent?: number | null;
  last_studied_at?: string | null;
  updated_at?: string | null;
  sources_count?: number;
  notes_count?: number;
  study_assets_count?: number;
  quizzes_count?: number;
  mode?: string;
};

export function formatRelativeTime(iso: string | null | undefined): string {
  if (!iso) return 'Not studied yet';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return 'Not studied yet';

  const now = Date.now();
  const diffMs = now - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} ${diffMins === 1 ? 'minute' : 'minutes'} ago`;
  if (diffHours < 24) return `${diffHours} ${diffHours === 1 ? 'hour' : 'hours'} ago`;
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 14) return 'Last week';
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function mapApiNotebookToLibrary(item: ApiNotebookListItem): LibraryNotebook {
  const subjectDisplay = item.subject?.trim() || '—';
  const classDisplay = item.class_level?.trim() || 'Set in notebook';

  return {
    id: item.slug,
    slug: item.slug,
    notebookId: item.id,
    mode: item.mode,
    subject: subjectDisplay,
    classLevel: classDisplay,
    title: item.title,
    subtitle: item.subtitle?.trim() || '—',
    focus: item.focus?.trim() || 'Set in notebook',
    masteryPercent: typeof item.mastery_percent === 'number' ? item.mastery_percent : 0,
    sources: item.sources_count ?? 0,
    studyAssets: item.study_assets_count ?? 0,
    quizzes: item.quizzes_count ?? 0,
    lastStudied: formatRelativeTime(item.last_studied_at ?? item.updated_at),
    lastStudiedAt: item.last_studied_at ?? item.updated_at ?? null,
  };
}
