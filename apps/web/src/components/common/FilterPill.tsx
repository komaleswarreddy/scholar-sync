'use client';

type FilterPillProps = {
  label: string;
  active: boolean;
  onClick: () => void;
};

export function FilterPill({ label, active, onClick }: FilterPillProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`library-filter-pill ${active ? 'library-filter-pill--active' : ''}`}
    >
      {label}
    </button>
  );
}
