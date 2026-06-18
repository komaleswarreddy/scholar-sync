'use client';

interface NotebookSaveNameDialogProps {
  open: boolean;
  title: string;
  isSaving?: boolean;
  onTitleChange: (value: string) => void;
  onSave: () => void | Promise<void>;
  onLeaveAnyway: () => void;
  onCancel: () => void;
}

export function NotebookSaveNameDialog({
  open,
  title,
  isSaving = false,
  onTitleChange,
  onSave,
  onLeaveAnyway,
  onCancel,
}: NotebookSaveNameDialogProps) {
  if (!open) return null;

  const trimmed = title.trim();
  const canSave = trimmed.length > 0 && trimmed.toLowerCase() !== 'untitled notebook';

  return (
    <div className="assets-modal-backdrop" role="presentation">
      <div className="assets-modal" role="dialog" aria-labelledby="notebook-save-title">
        <h2 id="notebook-save-title" className="assets-modal__title">
          Name your notebook
        </h2>
        <p className="text-[13px] text-[var(--color-home-text-muted)] mb-4">
          Give this notebook a name before leaving, or continue without saving.
        </p>
        <input
          className="library-search-input w-full mb-4"
          value={title}
          onChange={(e) => onTitleChange(e.target.value)}
          placeholder="Notebook name"
          autoFocus
        />
        <div className="flex flex-wrap gap-2 justify-end">
          <button type="button" className="profile-btn-secondary" onClick={onCancel}>
            Stay
          </button>
          <button type="button" className="profile-btn-secondary" onClick={onLeaveAnyway}>
            Leave without saving
          </button>
          <button
            type="button"
            className="profile-btn-primary"
            onClick={() => void onSave()}
            disabled={!canSave || isSaving}
          >
            {isSaving ? 'Saving...' : 'Save and leave'}
          </button>
        </div>
      </div>
    </div>
  );
}
