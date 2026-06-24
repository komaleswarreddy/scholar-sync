/**
 * Generated Studio Features — global recent outputs from the API.
 */

'use client';

import { FileText, X, Download } from 'lucide-react';
import { useAppToast } from '@/contexts/AppToastContext';
import { useDeleteStudioFeature, useStudioFeatures } from '@/hooks/useStudioFeatures';
import { StudyAssetsSkeleton } from '@/components/skeleton';
import { useStudioFeaturePreview } from '@/hooks/useStudioFeaturePreview';
import { hasStudioContent } from '@/lib/studio-display';
import { studioTypeLabel } from '@/lib/studio-content';
import { formatRelativeTime } from '@/lib/library-mapper';

export function GeneratedStudioFeatures({ variant = 'default' }: { variant?: 'default' | 'notebook' }) {
  const isNotebook = variant === 'notebook';
  const { showToast } = useAppToast();
  const { data: features = [], isLoading } = useStudioFeatures({ limit: 24 });
  const deleteFeature = useDeleteStudioFeature();
  const { openPreview } = useStudioFeaturePreview();

  const handleOpen = (feature: (typeof features)[number]) => {
    if (!hasStudioContent(feature.content)) {
      showToast('This asset has no content to display');
      return;
    }
    openPreview({
      id: feature.id,
      type: feature.type,
      title: feature.title,
      content: feature.content,
    });
  };

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    void deleteFeature.mutateAsync(id).catch(() => showToast('Could not delete asset'));
  };

  const handleDownload = (feature: (typeof features)[number], e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const content =
        typeof feature.content === 'string'
          ? feature.content
          : JSON.stringify(feature.content, null, 2);
      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${feature.title.toLowerCase().replace(/\s+/g, '-')}-${feature.id}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      showToast('Could not download asset');
    }
  };

  return (
    <div className={`flex flex-col ${isNotebook ? '' : 'h-full'}`}>
      {!isNotebook && (
        <div className="h-14 flex items-center justify-between px-4 border-b border-border-default flex-shrink-0">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-text-secondary" />
            <h2 className="text-lg font-medium text-text-primary">Generated Features</h2>
            {features.length > 0 && (
              <span className="text-xs text-text-secondary bg-surface-hover px-2 py-0.5 rounded-full">
                {features.length}
              </span>
            )}
          </div>
        </div>
      )}

      <div className={`${isNotebook ? 'max-h-48' : 'flex-1'} overflow-y-auto`}>
        {isLoading ? (
          <StudyAssetsSkeleton count={2} />
        ) : features.length === 0 ? (
          <div
            className={`flex flex-col items-center justify-center text-center ${isNotebook ? 'p-4' : 'h-full p-6'}`}
          >
            <FileText
              className={`${isNotebook ? 'w-8 h-8' : 'w-12 h-12'} text-text-tertiary mb-2 opacity-50`}
            />
            <p className={`${isNotebook ? 'text-[12px]' : 'text-sm'} text-text-secondary`}>
              Generated features will appear here automatically
            </p>
          </div>
        ) : (
          <div className={`${isNotebook ? 'px-4 pb-3 space-y-2' : 'p-4 space-y-3'}`}>
            {features.map((feature) => (
              <div
                key={feature.id}
                onClick={() => handleOpen(feature)}
                className="bg-surface-subtle rounded-lg border border-border-default overflow-hidden cursor-pointer hover:bg-surface-hover transition-colors"
              >
                <div className="p-3 flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-medium text-text-primary truncate">{feature.title}</h3>
                    <p className="text-xs text-text-secondary mt-0.5">
                      {feature.created_at
                        ? `${formatRelativeTime(feature.created_at)} • ${studioTypeLabel(feature.type)}`
                        : studioTypeLabel(feature.type)}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 ml-2" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={(e) => handleDownload(feature, e)}
                      className="p-1.5 hover:bg-surface-hover rounded transition-colors"
                      title="Download"
                      type="button"
                    >
                      <Download className="w-3.5 h-3.5 text-text-secondary" />
                    </button>
                    <button
                      onClick={(e) => handleDelete(feature.id, e)}
                      className="p-1.5 hover:bg-surface-hover rounded transition-colors"
                      title="Delete"
                      type="button"
                    >
                      <X className="w-3.5 h-3.5 text-text-secondary" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
