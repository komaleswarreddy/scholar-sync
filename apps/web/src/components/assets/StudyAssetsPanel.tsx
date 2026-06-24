'use client';

import { useCallback, useMemo, useState } from 'react';
import {
  ASSET_CLASS_FILTERS,
  ASSET_SUBJECT_FILTERS,
  ASSET_TYPE_FILTERS,
  type AssetClass,
  type AssetSubject,
  type StudyAsset,
} from '@/lib/assets-mock-data';
import { mapStudioFeatureToStudyAsset } from '@/lib/assets-mapper';
import { useAppToast } from '@/contexts/AppToastContext';
import { useListNotebooks } from '@/hooks/useNotebooks';
import { useDeleteStudioFeature, useStudioFeatures } from '@/hooks/useStudioFeatures';
import { StudyAssetsSkeleton } from '@/components/skeleton';
import { useStudioFeaturePreview } from '@/hooks/useStudioFeaturePreview';
import { AssetDeleteDialog } from './AssetDeleteDialog';
import { AssetEditModal } from './AssetEditModal';
import { AssetsSearchInput } from './AssetsSearchInput';
import { FilterPillRow } from './FilterPillRow';
import { StudyAssetCard } from './StudyAssetCard';

type StudyAssetsPanelProps = {
  searchInline?: boolean;
  query?: string;
  onQueryChange?: (q: string) => void;
  notebookId?: string;
};

export function StudyAssetsPanel({
  searchInline = false,
  query: controlledQuery,
  onQueryChange,
  notebookId,
}: StudyAssetsPanelProps) {
  const [internalQuery, setInternalQuery] = useState('');
  const query = controlledQuery ?? internalQuery;
  const setQuery = onQueryChange ?? setInternalQuery;
  const { showToast } = useAppToast();
  const { data: features = [], isLoading } = useStudioFeatures({
    notebookId,
    limit: 200,
  });
  const { data: notebookList } = useListNotebooks();
  const deleteFeature = useDeleteStudioFeature();
  const { openPreview } = useStudioFeaturePreview();

  const notebookLookup = useMemo(() => {
    const map = new Map<string, { title: string; subject?: string | null; class_level?: string | null }>();
    for (const nb of notebookList?.notebooks ?? []) {
      map.set(nb.id, {
        title: nb.title,
        subject: nb.subject,
        class_level: nb.class_level,
      });
    }
    return map;
  }, [notebookList?.notebooks]);

  const assets = useMemo(
    () =>
      features.map((feature) => {
        const nb = notebookLookup.get(feature.notebook_id);
        return mapStudioFeatureToStudyAsset(
          feature,
          nb?.title ?? 'Notebook',
          nb?.subject ?? '—',
          nb?.class_level ?? '—',
        );
      }),
    [features, notebookLookup],
  );

  const [pinnedIds, setPinnedIds] = useState<Set<string>>(new Set());
  const [editing, setEditing] = useState<StudyAsset | null>(null);
  const [deleting, setDeleting] = useState<StudyAsset | null>(null);
  const [localTitles, setLocalTitles] = useState<Record<string, string>>({});

  const [typeFilter, setTypeFilter] = useState<(typeof ASSET_TYPE_FILTERS)[number]>('All');
  const [subjectFilter, setSubjectFilter] =
    useState<(typeof ASSET_SUBJECT_FILTERS)[number]>('All Subjects');
  const [classFilter, setClassFilter] = useState<(typeof ASSET_CLASS_FILTERS)[number]>('All Classes');

  const displayAssets = useMemo(
    () =>
      assets.map((asset) => ({
        ...asset,
        title: localTitles[asset.id] ?? asset.title,
      })),
    [assets, localTitles],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = displayAssets.filter((a) => {
      if (typeFilter !== 'All' && a.type !== typeFilter) return false;
      if (subjectFilter !== 'All Subjects' && a.subject !== (subjectFilter as AssetSubject)) {
        return false;
      }
      if (classFilter !== 'All Classes' && a.classLevel !== (classFilter as AssetClass)) {
        return false;
      }
      if (q) {
        const hay = [a.title, a.type, a.notebook, a.subject, a.classLevel, a.meta]
          .join(' ')
          .toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    return [...list].sort((a, b) => {
      const ap = pinnedIds.has(a.id) ? 0 : 1;
      const bp = pinnedIds.has(b.id) ? 0 : 1;
      if (ap !== bp) return ap - bp;
      return 0;
    });
  }, [displayAssets, query, typeFilter, subjectFilter, classFilter, pinnedIds]);

  const togglePin = (id: string, title: string) => {
    setPinnedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
        showToast(`"${title}" unpinned`);
      } else {
        next.add(id);
        showToast(`"${title}" pinned to top`);
      }
      return next;
    });
  };

  const saveEdit = (newTitle: string) => {
    if (!editing) return;
    setLocalTitles((prev) => ({ ...prev, [editing.id]: newTitle }));
    showToast('Asset updated');
    setEditing(null);
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    const id = deleting.id;
    try {
      await deleteFeature.mutateAsync(id);
      setPinnedIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      showToast(`"${deleting.title}" deleted`);
    } catch {
      showToast('Could not delete asset');
    }
    setDeleting(null);
  };

  const handleOpen = useCallback(
    (asset: StudyAsset) => {
      const opened = openPreview({
        id: asset.id,
        type: asset.studioType ?? asset.type.toLowerCase().replace(' ', '_'),
        title: asset.title,
        content: asset.content,
      });
      if (!opened) showToast('This asset has no content to display');
    },
    [openPreview, showToast],
  );

  return (
    <div className="assets-panel" role="tabpanel">
      <div className="assets-filters-toolbar">
        <div className="assets-filters-stack assets-filters-stack--study">
          <FilterPillRow
            label="Filter by type"
            options={ASSET_TYPE_FILTERS}
            value={typeFilter}
            onChange={(value) => setTypeFilter(value as typeof typeFilter)}
          />
          <FilterPillRow
            label="Filter by class"
            options={ASSET_CLASS_FILTERS}
            value={classFilter}
            onChange={(value) => setClassFilter(value as typeof classFilter)}
          />
          <FilterPillRow
            label="Filter by subject"
            options={ASSET_SUBJECT_FILTERS}
            value={subjectFilter}
            onChange={(value) => setSubjectFilter(value as typeof subjectFilter)}
          />
        </div>

        {!searchInline && (
          <div className="assets-search-slot">
            <AssetsSearchInput value={query} onChange={setQuery} />
          </div>
        )}
      </div>

      {isLoading ? (
        <StudyAssetsSkeleton />
      ) : filtered.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((asset) => (
            <StudyAssetCard
              key={asset.id}
              asset={asset}
              isPinned={pinnedIds.has(asset.id)}
              onOpen={() => handleOpen(asset)}
              onPin={() => togglePin(asset.id, asset.title)}
              onEdit={() => setEditing(asset)}
              onDelete={() => setDeleting(asset)}
            />
          ))}
        </div>
      ) : (
        <p className="text-center text-[var(--color-home-text-muted)] py-10 text-[15px]">
          No study assets match your filters.
        </p>
      )}

      <AssetEditModal
        open={!!editing}
        title={editing?.title ?? ''}
        itemType="asset"
        onClose={() => setEditing(null)}
        onSave={saveEdit}
      />
      <AssetDeleteDialog
        open={!!deleting}
        itemName={deleting?.title ?? ''}
        itemType="asset"
        onClose={() => setDeleting(null)}
        onConfirm={confirmDelete}
      />
    </div>
  );
}
