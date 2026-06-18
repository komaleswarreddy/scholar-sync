'use client';

import { useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';

type AssetDeleteDialogProps = {
  open: boolean;
  itemName: string;
  itemType: 'asset' | 'note' | 'source';
  onClose: () => void;
  onConfirm: () => void;
};

export function AssetDeleteDialog({
  open,
  itemName,
  itemType,
  onClose,
  onConfirm,
}: AssetDeleteDialogProps) {
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
        className="assets-modal assets-modal--compact"
        role="alertdialog"
        aria-labelledby="asset-delete-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex gap-3">
          <div className="w-10 h-10 rounded-full bg-[#FEF2F2] flex items-center justify-center flex-shrink-0">
            <AlertTriangle className="w-5 h-5 text-[#DC2626]" />
          </div>
          <div>
            <h2 id="asset-delete-title" className="text-[17px] font-bold text-[var(--color-home-text)]">
              {itemType === 'source' ? 'Remove source?' : `Delete ${itemType}?`}
            </h2>
            <p className="text-[14px] text-[var(--color-home-text-muted)] mt-2 leading-relaxed">
              <span className="font-semibold text-[var(--color-home-text)]">{itemName}</span> will
              be removed from your{' '}
              {itemType === 'note'
                ? 'notes'
                : itemType === 'source'
                  ? 'notebook sources'
                  : 'study assets'}
              . This cannot be undone.
            </p>
          </div>
        </div>
        <div className="flex justify-end gap-3 mt-6">
          <button type="button" onClick={onClose} className="profile-btn-secondary">
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="assets-btn-danger"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
