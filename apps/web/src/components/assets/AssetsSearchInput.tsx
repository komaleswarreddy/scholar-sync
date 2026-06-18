'use client';

import { Search } from 'lucide-react';

type AssetsSearchInputProps = {
  value: string;
  onChange: (value: string) => void;
  className?: string;
  placeholder?: string;
};

export function AssetsSearchInput({
  value,
  onChange,
  className = '',
  placeholder = 'Search assets...',
}: AssetsSearchInputProps) {
  return (
    <div className={`assets-search-wrap ${className}`}>
      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="assets-search-input"
      />
      <Search className="assets-search-icon" strokeWidth={1.75} aria-hidden />
    </div>
  );
}
