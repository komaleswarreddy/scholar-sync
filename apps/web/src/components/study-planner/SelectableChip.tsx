'use client';

type SelectableChipProps = {
  label: string;
  selected: boolean;
  onClick: () => void;
  variant: 'subject' | 'chapter';
};

export function SelectableChip({ label, selected, onClick, variant }: SelectableChipProps) {
  const sizeClass =
    variant === 'subject' ? 'study-plan-chip--subject' : 'study-plan-chip--chapter';
  const selectedClass =
    variant === 'subject'
      ? 'study-plan-chip--selected-subject'
      : 'study-plan-chip--selected-chapter';

  return (
    <button
      type="button"
      className={`study-plan-chip ${sizeClass} ${selected ? selectedClass : ''}`}
      onClick={onClick}
      aria-pressed={selected}
    >
      {label}
    </button>
  );
}
