'use client';

import { FileText, FolderOpen } from 'lucide-react';

export type AssetsTab = 'study-assets' | 'notes';

type AssetsTabToggleProps = {
  active: AssetsTab;
  onChange: (tab: AssetsTab) => void;
};

export function AssetsTabToggle({ active, onChange }: AssetsTabToggleProps) {
  return (
    <div className="assets-tab-toggle" role="tablist" aria-label="Assets view">
      <button
        type="button"
        role="tab"
        aria-selected={active === 'study-assets'}
        onClick={() => onChange('study-assets')}
        className={`assets-tab-btn ${active === 'study-assets' ? 'assets-tab-btn--active' : ''}`}
      >
        <FolderOpen strokeWidth={1.75} aria-hidden />
        Study Assets
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={active === 'notes'}
        onClick={() => onChange('notes')}
        className={`assets-tab-btn ${active === 'notes' ? 'assets-tab-btn--active' : ''}`}
      >
        <FileText strokeWidth={1.75} aria-hidden />
        Notes
      </button>
    </div>
  );
}
