'use client';

import { useEffect } from 'react';
import { useNotebookContext } from '@/contexts/NotebookContext';
import { useSourceContext } from '@/contexts/SourceContext';
import { isVirtualNcertSourceId } from '@/lib/tutor-ncert-source';

/** Strip virtual NCERT rows from selection in tutor notebooks (UI hides them; NCERT global is used instead). */
export function TutorSourceBootstrap() {
  const { notebook } = useNotebookContext();
  const { setSelectedSources } = useSourceContext();

  useEffect(() => {
    if (notebook.mode !== 'tutor') return;
    setSelectedSources((prev) => {
      let changed = false;
      const next = new Set<string>();
      for (const id of prev) {
        if (isVirtualNcertSourceId(id)) {
          changed = true;
          continue;
        }
        next.add(id);
      }
      return changed ? next : prev;
    });
  }, [notebook.mode, setSelectedSources]);

  return null;
}
