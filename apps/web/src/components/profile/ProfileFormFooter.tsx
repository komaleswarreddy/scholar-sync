'use client';

type ProfileFormFooterProps = {
  onCancel?: () => void;
  onSave?: () => void;
  className?: string;
};

export function ProfileFormFooter({ onCancel, onSave, className = '' }: ProfileFormFooterProps) {
  return (
    <div
      className={`flex items-center justify-end gap-3 pt-6 mt-6 border-t border-[var(--color-home-border)] ${className}`}
    >
      <button type="button" onClick={onCancel} className="profile-btn-secondary">
        Cancel
      </button>
      <button type="button" onClick={onSave} className="profile-btn-primary">
        Save changes
      </button>
    </div>
  );
}
