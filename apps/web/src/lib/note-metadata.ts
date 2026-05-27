export type NoteFlagsV1 = {
  bookmarked?: boolean;
  /** V1 meaning for G/L filter: generated vs local */
  generated?: boolean;
};

const STORAGE_KEY = 'noteFlagsV1';

function readAll(): Record<string, NoteFlagsV1> {
  if (typeof window === 'undefined') return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return {};
    return parsed as Record<string, NoteFlagsV1>;
  } catch {
    return {};
  }
}

function writeAll(next: Record<string, NoteFlagsV1>) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // ignore
  }
}

export function getNoteFlags(noteId: string): NoteFlagsV1 {
  const all = readAll();
  return all[noteId] || {};
}

export function setNoteFlags(noteId: string, flags: NoteFlagsV1) {
  const all = readAll();
  all[noteId] = { ...all[noteId], ...flags };
  writeAll(all);
}

export function toggleNoteFlag(noteId: string, key: keyof NoteFlagsV1) {
  const current = getNoteFlags(noteId);
  setNoteFlags(noteId, { [key]: !current[key] } as NoteFlagsV1);
}

