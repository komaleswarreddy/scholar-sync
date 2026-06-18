'use client';

/** Small upward trend sparkline beside library stats */
export function LibrarySparkline() {
  return (
    <svg
      width="48"
      height="20"
      viewBox="0 0 48 20"
      fill="none"
      aria-hidden
      className="flex-shrink-0"
    >
      <path
        d="M2 14 L10 11 L18 12 L26 8 L34 6 L42 3"
        stroke="var(--color-brand-text)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="42" cy="3" r="2.5" fill="var(--color-brand-text)" />
    </svg>
  );
}
