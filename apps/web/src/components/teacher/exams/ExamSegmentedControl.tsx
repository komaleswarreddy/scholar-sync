'use client';

interface ExamSegmentedControlProps<T extends string> {
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
  label?: string;
}

export function ExamSegmentedControl<T extends string>({
  options,
  value,
  onChange,
  label,
}: ExamSegmentedControlProps<T>) {
  return (
    <div className="teacher-exam-segmented">
      {label && <span className="teacher-exam-segmented__label">{label}</span>}
      <div className="teacher-exam-segmented__control" role="group" aria-label={label}>
        {options.map((opt) => (
          <button
            key={opt.value}
            type="button"
            className={`teacher-exam-segmented__btn${
              value === opt.value ? ' teacher-exam-segmented__btn--active' : ''
            }`}
            onClick={() => onChange(opt.value)}
            aria-pressed={value === opt.value}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}
