'use client';

import { useState } from 'react';
import { ChevronDown, SlidersHorizontal } from 'lucide-react';
import { NOTE_SORT_OPTIONS } from '@/lib/assets-mock-data';

type AssetsSortDropdownProps = {
  value: (typeof NOTE_SORT_OPTIONS)[number];
  onChange: (value: (typeof NOTE_SORT_OPTIONS)[number]) => void;
  className?: string;
};

export function AssetsSortDropdown({ value, onChange, className = '' }: AssetsSortDropdownProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className={`assets-sort-wrap ${className}`}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="assets-sort-btn"
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        <SlidersHorizontal className="assets-sort-btn-icon" strokeWidth={1.75} />
        <span className="assets-sort-btn-label">{value}</span>
        <ChevronDown className="assets-sort-btn-chevron" strokeWidth={1.75} />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" aria-hidden onClick={() => setOpen(false)} />
          <ul className="assets-sort-menu" role="listbox">
            {NOTE_SORT_OPTIONS.map((opt) => (
              <li key={opt}>
                <button
                  type="button"
                  role="option"
                  aria-selected={value === opt}
                  onClick={() => {
                    onChange(opt);
                    setOpen(false);
                  }}
                  className={`assets-sort-menu-item ${value === opt ? 'assets-sort-menu-item--active' : ''}`}
                >
                  {opt}
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
