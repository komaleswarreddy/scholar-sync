'use client';

import Link from 'next/link';
import { useNotebookContext } from '@/contexts/NotebookContext';
import { MasteryRing } from '@/components/library/MasteryRing';
import {
  HEATMAP_CELL_COLORS,
  HEATMAP_LEGEND,
  normalizeHeatmapCells,
} from '@/lib/heatmap';

export function NotebookWeeklyMastery() {
  const { notebook } = useNotebookContext();
  const mastery = notebook.mastery_percent;
  const hasMastery = typeof mastery === 'number' && mastery >= 0;
  const heatmap = normalizeHeatmapCells(notebook.settings?.heatmap);
  const hasHeatmapData = heatmap.some((cell) => cell !== 'empty');

  return (
    <div className="notebook-col-section notebook-col-section--mastery">
      <div className="notebook-weekly-mastery">
        <div className="notebook-weekly-mastery-header">
          <span className="notebook-weekly-mastery-label">WEEKLY MASTERY</span>
          <Link href="/analytics" className="notebook-weekly-mastery-link">
            View full analytics
          </Link>
        </div>

        <div className="notebook-weekly-mastery-body">
          <div className="notebook-weekly-mastery-ring" aria-hidden>
            {hasMastery ? (
              <MasteryRing
                percent={mastery}
                strokeColor="var(--color-brand-text)"
                size={54}
                showCenterLabel
              />
            ) : (
              <div className="notebook-weekly-mastery-ring-empty">
                <span className="text-[11px] font-semibold text-[var(--color-home-label)]">—</span>
              </div>
            )}
          </div>
          <div className="notebook-weekly-mastery-info">
            <p className="notebook-weekly-mastery-subject">
              {notebook.subject || 'Your subject'}
            </p>
            <p className="notebook-weekly-mastery-focus">
              {notebook.focus
                ? `Focus: ${notebook.focus}`
                : 'Focus areas appear as you study'}
            </p>
            <p className="notebook-weekly-mastery-updated">
              {hasMastery ? 'Updated from your progress' : 'Start studying to track mastery'}
            </p>
          </div>
        </div>

        <p className="notebook-weekly-mastery-heatmap-label">Concept heatmap</p>
        {hasHeatmapData ? (
          <>
            <div className="notebook-heatmap" role="img" aria-label="Concept mastery heatmap">
              {heatmap.map((cell, index) => (
                <div
                  key={index}
                  className="notebook-heatmap-cell"
                  style={{ backgroundColor: HEATMAP_CELL_COLORS[cell] }}
                  title={cell}
                />
              ))}
            </div>
            <div className="notebook-heatmap-legend">
              {HEATMAP_LEGEND.map((item) => (
                <span key={item.level} className="notebook-heatmap-legend-item">
                  <span
                    className="notebook-heatmap-legend-dot"
                    style={{ backgroundColor: HEATMAP_CELL_COLORS[item.level] }}
                  />
                  {item.label}
                </span>
              ))}
            </div>
          </>
        ) : (
          <div className="notebook-heatmap-empty">
            <p className="text-[12px] text-[var(--color-home-text-muted)] leading-relaxed">
              Concept heatmap builds as you study topics in this notebook.
            </p>
            <Link href="/analytics" className="notebook-weekly-mastery-link inline-block mt-2">
              Open analytics
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
