import type { ContentType } from '@/components/studio/GenerationModal';

export function determineStudioContentType(taskType: string, content: unknown): ContentType {
  if (content && typeof content === 'object') {
    const obj = content as Record<string, unknown>;
    if (obj.task_type === 'quiz' || taskType === 'quiz') return 'json';
    if (obj.task_type === 'flashcards' || taskType === 'flashcards') return 'json';
    if (['mind_map', 'slide_deck'].includes(taskType)) {
      return 'markdown';
    }
    if (obj.content && typeof obj.content === 'string') {
      return ['mind_map', 'slide_deck'].includes(taskType) ? 'markdown' : 'text';
    }
    if (obj.data) return 'json';
  }
  if (typeof content === 'string' && content.trim()) {
    return ['mind_map', 'slide_deck'].includes(taskType) ? 'markdown' : 'text';
  }
  return 'text';
}

export function studioTypeLabel(type: string): string {
  return type.replace(/_/g, ' ');
}
