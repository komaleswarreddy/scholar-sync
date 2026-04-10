import { useMemo } from 'react';
import { useSources } from '@/hooks/useSources';
import { useSourceContext } from '@/contexts/SourceContext';

export function normalizeSourceId(id: unknown): string {
  return String(id ?? '').trim();
}

/**
 * IDs in `selectedSources` that still exist in the current sources list.
 * Keeps UI counts and API payloads aligned with visible checkboxes (prunes stale localStorage / deleted docs).
 */
export function useValidSelectedSourceIds() {
  const { data: sources = [] } = useSources();
  const { selectedSources } = useSourceContext();

  return useMemo(() => {
    const valid = new Set(sources.map((s) => normalizeSourceId(s.id)).filter(Boolean));
    const seen = new Set<string>();
    const ids: string[] = [];
    for (const raw of selectedSources) {
      const id = normalizeSourceId(raw);
      if (!id || !valid.has(id) || seen.has(id)) continue;
      seen.add(id);
      ids.push(id);
    }
    return { validSelectedIds: ids, validSelectedCount: ids.length };
  }, [sources, selectedSources]);
}
