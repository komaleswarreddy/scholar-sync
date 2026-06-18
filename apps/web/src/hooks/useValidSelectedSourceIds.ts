import { useMemo } from 'react';
import { useCombinedSources } from '@/hooks/useCombinedSources';
import { useSourceContext } from '@/contexts/SourceContext';
import { useNotebookScopeId } from '@/contexts/NotebookContext';

export function normalizeSourceId(id: unknown): string {
  return String(id ?? '').trim();
}

/**
 * IDs in `selectedSources` that still exist in the current sources list
 * (including virtual NCERT sources for tutor notebooks).
 */
export function useValidSelectedSourceIds() {
  const notebookId = useNotebookScopeId();
  const { sources } = useCombinedSources(notebookId);
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
