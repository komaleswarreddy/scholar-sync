'use client';

type NotebookSectionHeaderProps = {
  title: string;
  subtitle?: string;
  actionLabel?: string;
  onAction?: () => void;
  showAction?: boolean;
  className?: string;
};

export function NotebookSectionHeader({
  title,
  subtitle,
  actionLabel,
  onAction,
  showAction = true,
  className = '',
}: NotebookSectionHeaderProps) {
  return (
    <div className={className}>
      <div className="notebook-col-header px-4 pt-3 pb-1">
        <span>{title}</span>
        {showAction && actionLabel && onAction ? (
          <button type="button" className="notebook-link-btn" onClick={onAction}>
            {actionLabel}
          </button>
        ) : null}
      </div>
      {subtitle ? (
        <p className="px-4 text-[12px] text-[var(--color-home-text-muted)] mb-3">{subtitle}</p>
      ) : null}
    </div>
  );
}
