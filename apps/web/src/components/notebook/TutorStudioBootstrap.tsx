'use client';

import { useEffect, useRef } from 'react';
import { apiClient } from '@/lib/api-client';
import { useNotebookContextOptional } from '@/contexts/NotebookContext';
import { useTutorBootstrapOptional } from '@/contexts/TutorBootstrapContext';

/** Legacy fallback: skip when landing prep already generated assets or marked generation started. */
export function TutorStudioBootstrap() {
  const notebookCtx = useNotebookContextOptional();
  const bootstrapCtx = useTutorBootstrapOptional();
  const checkedRef = useRef(false);

  useEffect(() => {
    if (checkedRef.current) return;
    if (notebookCtx?.notebook.mode !== 'tutor') return;
    if (!notebookCtx?.notebook.id) return;

    const bootstrapSettings = notebookCtx.notebook.settings?.tutor_bootstrap;
    const studioStarted =
      typeof bootstrapSettings === 'object' &&
      bootstrapSettings &&
      Boolean((bootstrapSettings as Record<string, unknown>).studio_generation_started);
    if (studioStarted || bootstrapCtx?.studioGenerationStarted) {
      checkedRef.current = true;
      return;
    }

    checkedRef.current = true;

    void (async () => {
      try {
        const response = (await apiClient.listStudioFeatures({
          notebook_id: notebookCtx.notebook.id,
          limit: 10,
        })) as { features?: unknown[]; items?: unknown[] };
        const count = Array.isArray(response?.features)
          ? response.features.length
          : Array.isArray(response?.items)
            ? response.items.length
            : 0;
        if (count >= 2) {
          await apiClient.markTutorStudioGenerationStarted(notebookCtx.notebook.id);
        }
      } catch (error) {
        console.warn('[TutorStudioBootstrap] skip check failed:', error);
      }
    })();
  }, [bootstrapCtx?.studioGenerationStarted, notebookCtx]);

  return null;
}
