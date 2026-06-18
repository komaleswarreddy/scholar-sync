'use client';

import { FilterPill } from '@/components/common/FilterPill';

type FilterPillRowProps = {
  label: string;
  options: readonly string[];
  value: string;
  onChange: (value: string) => void;
};

export function FilterPillRow({ label, options, value, onChange }: FilterPillRowProps) {
  return (
    <div className="assets-filter-group">
      <span className="assets-filter-label">{label}</span>
      <div className="assets-filter-pills-row">
        {options.map((opt) => (
          <FilterPill
            key={opt}
            label={opt}
            active={value === opt}
            onClick={() => onChange(opt)}
          />
        ))}
      </div>
    </div>
  );
}
