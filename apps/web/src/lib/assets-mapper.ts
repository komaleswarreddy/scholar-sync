import type { AssetType, StudyAsset } from '@/lib/assets-mock-data';
import type { StudioFeature } from '@/hooks/useStudioFeatures';
import { formatRelativeTime } from '@/lib/library-mapper';

const TYPE_LABELS: Record<string, AssetType> = {
  quiz: 'Quiz',
  flashcards: 'Flashcards',
  mind_map: 'Mind Map',
  slide_deck: 'Summary',
  audio: 'Audio',
};

export function studioTypeToAssetType(type: string): AssetType {
  return TYPE_LABELS[type] ?? 'Summary';
}

export function studioFeatureMeta(type: string, content: unknown): string {
  if (type === 'quiz' && content && typeof content === 'object') {
    const data = (content as { data?: { questions?: unknown[] } }).data ?? content;
    const questions = (data as { questions?: unknown[] }).questions;
    if (Array.isArray(questions)) {
      return `${questions.length} questions`;
    }
  }
  if (type === 'flashcards' && content && typeof content === 'object') {
    const data = (content as { data?: unknown[] }).data ?? content;
    if (Array.isArray(data)) {
      return `${data.length} cards`;
    }
  }
  return 'Interactive';
}

export function mapStudioFeatureToStudyAsset(
  feature: StudioFeature,
  notebookTitle = 'Notebook',
  subject = '—',
  classLevel = '—',
): StudyAsset {
  return {
    id: feature.id,
    type: studioTypeToAssetType(feature.type),
    studioType: feature.type,
    title: feature.title,
    notebook: notebookTitle,
    subject: subject as StudyAsset['subject'],
    classLevel: classLevel as StudyAsset['classLevel'],
    meta: studioFeatureMeta(feature.type, feature.content),
    timestamp: formatRelativeTime(feature.created_at),
    content: feature.content,
  };
}
