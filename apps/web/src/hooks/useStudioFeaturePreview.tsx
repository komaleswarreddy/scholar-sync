'use client';

import { useStudioPreview } from '@/contexts/StudioPreviewContext';
import { hasStudioContent } from '@/lib/studio-display';

export type PreviewableStudioFeature = {
  id?: string;
  type: string;
  title: string;
  content: unknown;
};

export function useStudioFeaturePreview() {
  const preview = useStudioPreview();

  const openPreview = (feature: PreviewableStudioFeature) => {
    if (!hasStudioContent(feature.content)) return false;
    preview.openPreview(feature);
    return true;
  };

  return {
    openPreview,
    closePreview: preview.closePreview,
    modal: null,
  };
}
