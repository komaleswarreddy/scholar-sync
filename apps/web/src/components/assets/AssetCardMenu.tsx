'use client';

import { useEffect, useRef, useState } from 'react';
import { MoreVertical, Pin, PinOff, Pencil, Trash2 } from 'lucide-react';

export type AssetCardMenuProps = {
  isPinned?: boolean;
  onPin: () => void;
  onEdit: () => void;
  onDelete: () => void;
  menuLabel?: string;
};

export function AssetCardMenu({
  isPinned = false,
  onPin,
  onEdit,
  onDelete,
  menuLabel = 'Asset options',
}: AssetCardMenuProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleOutside = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', handleOutside);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handleOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [open]);

  const run = (action: () => void) => {
    setOpen(false);
    action();
  };

  return (
    <div
      className="assets-card-menu"
      ref={rootRef}
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.stopPropagation()}
    >
      <button
        type="button"
        className={`assets-card-menu-trigger ${open ? 'assets-card-menu-trigger--open' : ''}`}
        aria-label={menuLabel}
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={(e) => {
          e.stopPropagation();
          setOpen((o) => !o);
        }}
      >
        <MoreVertical className="w-4 h-4" />
      </button>

      {open && (
        <ul className="assets-card-menu-dropdown" role="menu">
          <li role="none">
            <button
              type="button"
              role="menuitem"
              className="assets-card-menu-item"
              onClick={() => run(onPin)}
            >
              {isPinned ? (
                <PinOff className="w-4 h-4" strokeWidth={1.75} />
              ) : (
                <Pin className="w-4 h-4" strokeWidth={1.75} />
              )}
              {isPinned ? 'Unpin' : 'Pin'}
            </button>
          </li>
          <li role="none">
            <button
              type="button"
              role="menuitem"
              className="assets-card-menu-item"
              onClick={() => run(onEdit)}
            >
              <Pencil className="w-4 h-4" strokeWidth={1.75} />
              Edit
            </button>
          </li>
          <li role="none" className="assets-card-menu-divider" />
          <li role="none">
            <button
              type="button"
              role="menuitem"
              className="assets-card-menu-item assets-card-menu-item--danger"
              onClick={() => run(onDelete)}
            >
              <Trash2 className="w-4 h-4" strokeWidth={1.75} />
              Delete
            </button>
          </li>
        </ul>
      )}
    </div>
  );
}
