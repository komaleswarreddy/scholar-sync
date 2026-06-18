'use client';

import { useEffect, useState } from 'react';
import { X } from 'lucide-react';

type AssetEditModalProps = {
  open: boolean;
  title: string;
  itemType: 'asset' | 'note';
  onClose: () => void;
  onSave: (newTitle: string) => void;
};

export function AssetEditModal({
  open,
  title,
  itemType,
  onClose,
  onSave,
}: AssetEditModalProps) {
  const [value, setValue] = useState(title);

  useEffect(() => {
    if (open) setValue(title);
  }, [open, title]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="assets-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="assets-modal"
        role="dialog"
        aria-labelledby="asset-edit-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 id="asset-edit-title" className="text-[17px] font-bold text-[var(--color-home-text)]">
            Edit {itemType === 'note' ? 'note' : 'asset'}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-md text-[var(--color-home-label)] hover:bg-[var(--color-brand-surface)]"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <label className="profile-field-label" htmlFor="asset-edit-input">
          Title
        </label>
        <input
          id="asset-edit-input"
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="library-search-input w-full px-4 py-2.5 text-[14px] mt-1"
          autoFocus
        />
        <div className="flex justify-end gap-3 mt-6">
          <button type="button" onClick={onClose} className="profile-btn-secondary">
            Cancel
          </button>
          <button
            type="button"
            onClick={() => {
              const trimmed = value.trim();
              if (trimmed) onSave(trimmed);
            }}
            className="profile-btn-primary"
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
