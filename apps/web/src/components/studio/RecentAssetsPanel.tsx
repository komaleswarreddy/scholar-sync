'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { FileText, HelpCircle, Layers, Network } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useNotebookContext } from '@/contexts/NotebookContext';
import { useAppToast } from '@/contexts/AppToastContext';
import { useValidSelectedSourceIds } from '@/hooks/useValidSelectedSourceIds';
import { filterRealSourceIds } from '@/lib/tutor-ncert-source';
import { useCreateStudioFeature, useStudioFeatures } from '@/hooks/useStudioFeatures';
import { useStudioFeaturePreview } from '@/hooks/useStudioFeaturePreview';
import { hasStudioContent } from '@/lib/studio-display';
import { formatRelativeTime } from '@/lib/library-mapper';
import { studioTypeLabel } from '@/lib/studio-content';
import { NotebookSectionHeader } from '@/components/notebook/NotebookSectionHeader';

const TYPE_ICONS: Record<string, LucideIcon> = {
  quiz: HelpCircle,
  flashcards: Layers,
  mind_map: Network,
  slide_deck: FileText,
};

const LOCAL_STORAGE_KEY = 'generatedStudioFeatures';
const LOCAL_STORAGE_MIGRATED_KEY = 'generatedStudioFeaturesMigrated';

const COMPACT_COLLAPSED_LIMIT = 1;
const COMPACT_EXPANDED_LIMIT = 12;

interface RecentAssetsPanelProps {
  variant?: 'default' | 'compact';
  maxItems?: number;
}

export function RecentAssetsPanel({ variant = 'default', maxItems = 4 }: RecentAssetsPanelProps) {
  const isCompact = variant === 'compact';
  const [assetsExpanded, setAssetsExpanded] = useState(false);
  const { notebookId } = useNotebookContext();
  const { showToast } = useAppToast();
  const fetchLimit = isCompact
    ? assetsExpanded
      ? COMPACT_EXPANDED_LIMIT
      : 2
    : maxItems;
  const { data: features = [], isLoading } = useStudioFeatures({
    notebookId,
    limit: fetchLimit,
  });
  const createFeature = useCreateStudioFeature();
  const { validSelectedIds } = useValidSelectedSourceIds();
  const { openPreview } = useStudioFeaturePreview();
  const migratedRef = useRef(false);

  useEffect(() => {
    if (migratedRef.current || !notebookId) return;
    if (localStorage.getItem(LOCAL_STORAGE_MIGRATED_KEY) === '1') return;

    migratedRef.current = true;
    const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(LOCAL_STORAGE_MIGRATED_KEY, '1');
      return;
    }

    try {
      const parsed = JSON.parse(raw) as Array<{
        type: string;
        title: string;
        content: unknown;
      }>;
      if (!Array.isArray(parsed) || parsed.length === 0) {
        localStorage.removeItem(LOCAL_STORAGE_KEY);
        localStorage.setItem(LOCAL_STORAGE_MIGRATED_KEY, '1');
        return;
      }

      void (async () => {
        try {
          for (const item of parsed) {
            if (!item?.type || !item.title) continue;
            await createFeature.mutateAsync({
              notebook_id: notebookId,
              type: item.type,
              title: item.title,
              content: item.content,
            });
          }
        } finally {
          localStorage.removeItem(LOCAL_STORAGE_KEY);
          localStorage.setItem(LOCAL_STORAGE_MIGRATED_KEY, '1');
        }
      })();
    } catch {
      localStorage.setItem(LOCAL_STORAGE_MIGRATED_KEY, '1');
    }
  }, [notebookId, createFeature]);

  useEffect(() => {
    const onGenerated = (event: Event) => {
      const detail = (event as CustomEvent).detail as {
        type: string;
        title: string;
        content: unknown;
        source_ids?: string[];
      };
      if (!detail?.type || !notebookId) return;
      void createFeature
        .mutateAsync({
          notebook_id: notebookId,
          type: detail.type,
          title: detail.title,
          content: detail.content,
          source_ids: filterRealSourceIds(detail.source_ids ?? validSelectedIds),
        })
        .catch(() => showToast('Could not save asset'));
    };

    window.addEventListener('studioFeatureGenerated', onGenerated as EventListener);
    return () => window.removeEventListener('studioFeatureGenerated', onGenerated as EventListener);
  }, [notebookId, createFeature, showToast, validSelectedIds]);

  const visibleFeatures = isCompact
    ? assetsExpanded
      ? features
      : features.slice(0, COMPACT_COLLAPSED_LIMIT)
    : features;

  const canExpandCompact = isCompact && (features.length > COMPACT_COLLAPSED_LIMIT || assetsExpanded);

  return (
    <div className="flex flex-col">
      {isCompact ? (
        <NotebookSectionHeader
          title="RECENT ASSETS"
          actionLabel={assetsExpanded ? 'Show less' : 'View all'}
          onAction={() => setAssetsExpanded((open) => !open)}
          showAction={canExpandCompact || assetsExpanded}
        />
      ) : (
        <div className="notebook-col-header px-4 pt-3 pb-1 flex items-center justify-between gap-2">
          <span>RECENT ASSETS</span>
          <Link
            href={`/assets?notebook=${encodeURIComponent(notebookId)}`}
            className="notebook-link-btn text-[11px] font-semibold"
          >
            View all
          </Link>
        </div>
      )}

      <div
        className={`overflow-y-auto px-4 pb-3 space-y-2 ${
          isCompact ? (assetsExpanded ? 'max-h-48' : 'max-h-20') : 'max-h-48'
        }`}
      >
        {isLoading ? (
          <p className="text-[12px] text-[var(--color-home-text-muted)] py-2">Loading assets...</p>
        ) : visibleFeatures.length === 0 ? (
          isCompact ? null : (
            <p className="text-[12px] text-[var(--color-home-text-muted)] py-2 leading-relaxed">
              Study assets you generate in this notebook will appear here. View all notebooks on
              Assets.
            </p>
          )
        ) : (
          visibleFeatures.map((feature) => {
            const Icon = TYPE_ICONS[feature.type] ?? FileText;
            return (
              <button
                key={feature.id}
                type="button"
                className={`notebook-recent-item w-full text-left hover:bg-[var(--color-brand-surface)] transition-colors ${isCompact ? 'py-2' : ''}`}
                onClick={() => {
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
                }}
              >
                <div
                  className={`rounded-lg bg-[var(--color-brand-surface)] flex items-center justify-center flex-shrink-0 ${isCompact ? 'w-7 h-7' : 'w-8 h-8'}`}
                >
                  <Icon
                    className={`text-[var(--color-brand-text)] ${isCompact ? 'w-3.5 h-3.5' : 'w-4 h-4'}`}
                    strokeWidth={1.75}
                  />
                </div>
                <div className="min-w-0 flex-1">
                  <p
                    className={`font-semibold text-[var(--color-home-text)] truncate ${isCompact ? 'text-[12px]' : 'text-[13px]'}`}
                  >
                    {feature.title}
                  </p>
                  <p className="text-[11px] text-[var(--color-home-text-muted)] mt-0.5">
                    {studioTypeLabel(feature.type)} • {formatRelativeTime(feature.created_at)}
                  </p>
                </div>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
