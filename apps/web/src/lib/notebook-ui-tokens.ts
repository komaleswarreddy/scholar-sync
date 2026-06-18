import type { LucideIcon } from 'lucide-react';
import { BookOpen, FileText, FileType, Globe } from 'lucide-react';

export type NotebookIconTone = 'green' | 'purple' | 'orange' | 'blue';

export const NOTEBOOK_TONE_STYLES: Record<
  NotebookIconTone,
  { bg: string; color: string; Icon: LucideIcon }
> = {
  green: { bg: '#E8F2EE', color: '#0F7A52', Icon: FileText },
  purple: { bg: '#F3E8FF', color: '#7C3AED', Icon: FileType },
  orange: { bg: '#FFF4EC', color: '#EA580C', Icon: FileText },
  blue: { bg: '#E8F0FE', color: '#1A73E8', Icon: BookOpen },
};

export const NOTEBOOK_STUDIO_TONE_STYLES: Record<
  NotebookIconTone,
  { bg: string; color: string }
> = {
  green: { bg: '#E8F2EE', color: '#0F7A52' },
  purple: { bg: '#F3E8FF', color: '#7C3AED' },
  orange: { bg: '#FFF4EC', color: '#EA580C' },
  blue: { bg: '#E8F0FE', color: '#1A73E8' },
};

export function getSourceToneFromType(type?: string): NotebookIconTone {
  const normalized = (type || '').toLowerCase();
  if (normalized.includes('pdf')) return 'green';
  if (normalized.includes('url') || normalized.includes('http')) return 'blue';
  if (normalized.includes('txt') || normalized.includes('text') || normalized.includes('note')) {
    return 'purple';
  }
  return 'orange';
}

export function getSourceToneStyle(type?: string) {
  const tone = getSourceToneFromType(type);
  return { tone, ...NOTEBOOK_TONE_STYLES[tone] };
}

export function formatNoteTitle(content?: string): string {
  const line = (content || '').trim().split('\n')[0]?.trim() || '';
  if (!line) return 'Untitled note';
  return line.length > 48 ? `${line.slice(0, 48)}…` : line;
}

export function formatRelativeTime(iso?: string): string {
  if (!iso) return 'Just now';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return 'Recently';
  const diffMs = Date.now() - date.getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days} days ago`;
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}
