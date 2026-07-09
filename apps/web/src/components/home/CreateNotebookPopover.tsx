'use client';

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { useRouter } from 'next/navigation';
import {
  ChevronRight,
  Compass,
  GraduationCap,
  Loader2,
  NotebookPen,
} from 'lucide-react';
import { TOAST_MIN_VISIBLE_MS, useAppToast } from '@/contexts/AppToastContext';
import { useCreateNotebook } from '@/hooks/useNotebooks';
import { track } from '@/lib/telemetry';

const NOTEBOOK_MODES = [
  {
    id: 'exploratory' as const,
    label: 'Exploratory',
    description: 'Upload sources, chat, and generate study assets',
    features: ['Sources', 'Chat', 'Studio'],
    available: true,
  },
  {
    id: 'tutor' as const,
    label: 'Tutor mode',
    description: 'Guided lessons with step-by-step coaching',
    features: ['NCERT', 'Quizzes', 'Progress'],
    available: true,
  },
] as const;

interface CreateNotebookPopoverProps {
  open: boolean;
  onClose: () => void;
  onCreated: (slug: string) => void;
}

export function CreateNotebookPopover({
  open,
  onClose,
  onCreated,
}: CreateNotebookPopoverProps) {
  const router = useRouter();
  const createNotebook = useCreateNotebook();
  const { showToast } = useAppToast();
  const [error, setError] = useState<string | null>(null);
  const [pendingMode, setPendingMode] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!open) {
      setError(null);
      setPendingMode(null);
      return;
    }
    setError(null);
    setPendingMode(null);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [open, onClose]);

  if (!open || !mounted) return null;

  const handleSelectMode = async (modeId: 'exploratory' | 'tutor') => {
    if (!NOTEBOOK_MODES.find((m) => m.id === modeId)?.available) return;

    setError(null);
    setPendingMode(modeId);
    track('home.create_notebook_mode_selected', { mode: modeId });

    if (modeId === 'tutor') {
      onClose();
      router.push('/tutor');
      return;
    }

    try {
      const notebook = await createNotebook.mutateAsync({
        title: 'Untitled notebook',
        mode: modeId,
      });
      onClose();
      void showToast('Notebook created', { minVisibleMs: TOAST_MIN_VISIBLE_MS });
      onCreated(notebook.slug);
    } catch (err) {
      setPendingMode(null);
      setError(err instanceof Error ? err.message : 'Failed to create notebook');
    }
  };

  return createPortal(
    <div className="assets-modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="assets-modal assets-modal--compact create-notebook-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-notebook-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex gap-3">
          <div className="w-10 h-10 rounded-full bg-[#E8F2EE] flex items-center justify-center flex-shrink-0">
            <NotebookPen className="w-5 h-5 text-[#0D3D2E]" strokeWidth={1.75} />
          </div>
          <div className="min-w-0">
            <h2
              id="create-notebook-title"
              className="text-[17px] font-bold text-[var(--color-home-text)] leading-snug"
            >
              Create notebook
            </h2>
            <p className="text-[14px] text-[var(--color-home-text-muted)] mt-2 leading-relaxed">
              Choose how you want to study. Select a mode and your notebook will open
              instantly.
            </p>
          </div>
        </div>

        <p className="home-section-label create-notebook-modal__list-label">Study modes</p>

        <ul className="create-notebook-modal__list" role="listbox" aria-label="Notebook modes">
          {NOTEBOOK_MODES.map((mode) => {
            const isPending = pendingMode === mode.id && createNotebook.isPending;
            const isDisabled = !mode.available || createNotebook.isPending;

            return (
              <li key={mode.id} className="create-notebook-modal__list-item">
                <button
                  type="button"
                  role="option"
                  aria-selected={mode.available}
                  aria-disabled={!mode.available}
                  className={[
                    'create-notebook-option',
                    mode.available ? 'create-notebook-option--available' : 'create-notebook-option--soon',
                    isPending ? 'create-notebook-option--loading' : '',
                  ]
                    .filter(Boolean)
                    .join(' ')}
                  onClick={() => handleSelectMode(mode.id)}
                  disabled={isDisabled}
                >
                  <span
                    className={[
                      'create-notebook-option__icon',
                      mode.id === 'exploratory'
                        ? 'create-notebook-option__icon--exploratory'
                        : 'create-notebook-option__icon--tutor',
                    ].join(' ')}
                  >
                    {isPending ? (
                      <Loader2 className="w-[18px] h-[18px] animate-spin" />
                    ) : mode.id === 'exploratory' ? (
                      <Compass className="w-[18px] h-[18px]" strokeWidth={1.75} />
                    ) : (
                      <GraduationCap className="w-[18px] h-[18px]" strokeWidth={1.75} />
                    )}
                  </span>

                  <span className="create-notebook-option__content">
                    <span className="create-notebook-option__row">
                      <span className="create-notebook-option__label">{mode.label}</span>
                      {!mode.available ? (
                        <span className="create-notebook-option__badge">Coming soon</span>
                      ) : null}
                    </span>
                    <span className="create-notebook-option__desc">{mode.description}</span>
                    <span className="create-notebook-option__features">
                      {mode.features.map((feature) => (
                        <span key={feature} className="create-notebook-option__feature">
                          {feature}
                        </span>
                      ))}
                    </span>
                  </span>

                  {mode.available ? (
                    <ChevronRight
                      className="create-notebook-option__chevron"
                      strokeWidth={2}
                      aria-hidden="true"
                    />
                  ) : null}
                </button>
              </li>
            );
          })}
        </ul>

        {error ? <p className="create-notebook-modal__error">{error}</p> : null}

        <div className="flex justify-end gap-3 mt-6">
          <button type="button" onClick={onClose} className="profile-btn-secondary">
            Cancel
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
