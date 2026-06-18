'use client';

import { ChevronDown, Calendar } from 'lucide-react';
import type { ReactNode } from 'react';

type ProfileFieldProps = {
  label: string;
  value?: string;
  type?: 'input' | 'select';
  colSpan?: 1 | 2 | 3;
  prefix?: ReactNode;
};

export function ProfileField({
  label,
  value,
  type = 'input',
  colSpan = 1,
  prefix,
}: ProfileFieldProps) {
  const spanClass =
    colSpan === 3 ? 'sm:col-span-3' : colSpan === 2 ? 'sm:col-span-2' : '';

  const valueEl = (
    <div
      className={`profile-field-value ${type === 'select' ? 'profile-field-value--select' : ''}`}
    >
      <span className="flex-1 truncate">{value}</span>
      {type === 'select' && (
        <ChevronDown className="w-4 h-4 text-[var(--color-home-label)] flex-shrink-0" />
      )}
      {label === 'Date of birth' && (
        <Calendar className="w-4 h-4 text-[var(--color-home-label)] flex-shrink-0" />
      )}
    </div>
  );

  return (
    <div className={spanClass}>
      <label className="profile-field-label">{label}</label>
      {prefix ? (
        <div className="profile-field-control">
          <div className="profile-field-prefix">{prefix}</div>
          {valueEl}
        </div>
      ) : (
        valueEl
      )}
    </div>
  );
}
