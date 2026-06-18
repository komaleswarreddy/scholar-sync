import type { NotebookRecord } from '@/contexts/NotebookContext';
import type { Source } from '@/hooks/useSources';

export const VIRTUAL_NCERT_SOURCE_PREFIX = 'ncert:';

export interface TutorScopeSettings {
  class_num?: number;
  subject_key?: string;
  subject_slug?: string;
  subsubject?: string | null;
  chapter_no?: number;
  chapter_name?: string;
  chapter_title?: string;
  filter_chapter_name?: string;
  ncert_document_id?: string | null;
  /** Indexed chunk count from ncert_global_documents (Pinecone NcertDataGlobal). */
  chunks_count?: number;
  concept?: string | null;
}

export function parseTutorScope(
  settings?: Record<string, unknown> | null,
): TutorScopeSettings | null {
  if (!settings || typeof settings !== 'object') return null;
  const scope = settings.tutor_scope;
  if (!scope || typeof scope !== 'object') return null;
  return scope as TutorScopeSettings;
}

export function virtualNcertSourceId(documentId: string): string {
  return `${VIRTUAL_NCERT_SOURCE_PREFIX}${documentId}`;
}

export function isVirtualNcertSourceId(id: string): boolean {
  return String(id ?? '').trim().startsWith(VIRTUAL_NCERT_SOURCE_PREFIX);
}

export function extractNcertDocumentIdFromVirtualSource(id: string): string | null {
  const trimmed = String(id ?? '').trim();
  if (!isVirtualNcertSourceId(trimmed)) return null;
  const docId = trimmed.slice(VIRTUAL_NCERT_SOURCE_PREFIX.length).trim();
  return docId || null;
}

export function filterRealSourceIds(ids: string[]): string[] {
  return ids.filter((id) => !isVirtualNcertSourceId(id));
}

function subjectDisplayLabel(scope: TutorScopeSettings): string {
  const key = scope.subject_key || scope.subject_slug || 'science';
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

export function formatTutorScopeChip(scope: TutorScopeSettings): string {
  const parts: string[] = [];
  if (scope.class_num != null) {
    parts.push(`Class ${scope.class_num}`);
  }
  parts.push(subjectDisplayLabel(scope));
  const chapterTitle = scope.chapter_title || scope.chapter_name;
  if (scope.chapter_no != null && chapterTitle) {
    parts.push(`Ch. ${scope.chapter_no} ${chapterTitle}`);
  } else if (scope.chapter_no != null) {
    parts.push(`Ch. ${scope.chapter_no}`);
  }
  if (scope.concept && String(scope.concept).trim()) {
    parts.push(String(scope.concept).trim());
  }
  return parts.join(' · ');
}

export function buildVirtualNcertSource(scope: TutorScopeSettings): Source | null {
  const docId = scope.ncert_document_id;
  if (!docId) return null;

  const chapterTitle = scope.chapter_title || scope.chapter_name || 'Chapter';
  const subjectLabel = subjectDisplayLabel(scope);
  const classNum = scope.class_num ?? '';
  const chapterNo = scope.chapter_no;
  const title =
    chapterNo != null
      ? `NCERT Class ${classNum} ${subjectLabel} — Ch.${chapterNo}: ${chapterTitle}`
      : `NCERT Class ${classNum} ${subjectLabel}`;

  return {
    id: virtualNcertSourceId(docId),
    title,
    file_name: `${chapterTitle}.pdf`,
    file_type: 'pdf',
    file_size: 0,
    upload_date: new Date().toISOString(),
    status: 'indexed',
    chunks_count:
      typeof scope.chunks_count === 'number' && scope.chunks_count >= 0
        ? scope.chunks_count
        : undefined,
  };
}

export function buildVirtualNcertSourceFromNotebook(notebook: NotebookRecord): Source | null {
  if (notebook.mode !== 'tutor') return null;
  const scope = parseTutorScope(notebook.settings ?? null);
  if (!scope) return null;
  return buildVirtualNcertSource(scope);
}

export function buildNcertGlobalApiParams(
  scope: TutorScopeSettings | null | undefined,
): {
  include_ncert_global: true;
  ncert_class: number;
  ncert_subject: string;
  ncert_chapter_no?: number;
  ncert_chapter_name?: string;
} | null {
  if (!scope) return null;
  const ncertClass = scope.class_num;
  const subject = String(scope.subject_slug ?? scope.subject_key ?? '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '_');
  const chapterNo = scope.chapter_no;
  const chapterName = String(
    scope.filter_chapter_name ?? scope.chapter_name ?? scope.chapter_title ?? '',
  )
    .trim()
    .toLowerCase();
  if (ncertClass == null || !subject) return null;
  if (chapterNo == null && !chapterName) return null;
  return {
    include_ncert_global: true,
    ncert_class: ncertClass,
    ncert_subject: subject,
    ...(chapterNo != null ? { ncert_chapter_no: chapterNo } : {}),
    ...(chapterName ? { ncert_chapter_name: chapterName } : {}),
  };
}

export function ncertDocumentFileUrl(documentId: string): string {
  return `/api/v1/tutor/ncert-documents/${encodeURIComponent(documentId)}/file`;
}
