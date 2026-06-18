'use client';

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import Link from 'next/link';
import { Calendar, ExternalLink, PlayCircle, X } from 'lucide-react';
import type { StudyModule } from '@/lib/study-planner-types';
import { formatModuleDate } from '@/lib/study-planner-utils';

type ModuleDetailModalProps = {
  module: StudyModule | null;
  onClose: () => void;
  onStartNotebook: (module: StudyModule) => void;
  onSkipModule: (module: StudyModule) => void;
  planName?: string;
  planHref?: string;
};

export function ModuleDetailModal({
  module,
  onClose,
  onStartNotebook,
  onSkipModule,
  planName,
  planHref,
}: ModuleDetailModalProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!module) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [module, onClose]);

  if (!module || !mounted) return null;

  const assets = module.preparedAssets;
  const assetParts: string[] = [];
  if (assets?.summary) assetParts.push('Summary');
  if (assets?.prompts) assetParts.push(`${assets.prompts} prompts`);
  if (assets?.flashcards) assetParts.push(`${assets.flashcards} flashcards`);
  if (assets?.quizQuestions) assetParts.push(`${assets.quizQuestions} quiz questions`);

  return createPortal(
    <div
      className="study-plan-module-modal-overlay study-plan-page"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="study-plan-module-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="module-modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <button type="button" className="study-plan-module-modal__close" onClick={onClose}>
          <X className="w-5 h-5" strokeWidth={2} />
        </button>

        <h2 id="module-modal-title" className="study-plan-module-modal__title">
          {module.title}
        </h2>

        <div className="study-plan-module-modal__pills">
          <span className="study-plan-module-modal__pill study-plan-module-modal__pill--subject">
            {module.subject}
          </span>
          <span className="study-plan-module-modal__pill study-plan-module-modal__pill--chapter">
            Ch. {module.chapterNo} · {module.chapterTitle}
          </span>
          {planName ? (
            <span className="study-plan-module-modal__pill study-plan-module-modal__pill--plan">
              {planName}
            </span>
          ) : null}
        </div>

        {planHref ? (
          <Link href={planHref} className="study-plan-module-modal__open-plan" onClick={onClose}>
            Open plan
            <ExternalLink className="w-4 h-4" strokeWidth={2} />
          </Link>
        ) : null}

        <div className="study-plan-module-modal__info">
          <span className="study-plan-module-modal__info-item">
            <Calendar className="w-4 h-4" strokeWidth={1.75} />
            {formatModuleDate(module.scheduledDate)}
          </span>
        </div>

        {module.description && (
          <p className="study-plan-module-modal__description">{module.description}</p>
        )}

        {assetParts.length > 0 && (
          <p className="study-plan-module-modal__prepared">
            Prepared for you: {assetParts.join(', ')}
          </p>
        )}

        <div className="study-plan-module-modal__divider" />

        <p className="study-plan-module-modal__ready-label">READY TO START?</p>

        <button
          type="button"
          className="study-plan-module-modal__start"
          onClick={() => onStartNotebook(module)}
        >
          <PlayCircle className="w-5 h-5" strokeWidth={2} />
          Start Notebook
        </button>

        <button
          type="button"
          className="study-plan-module-modal__skip"
          onClick={() => onSkipModule(module)}
        >
          Skip Module
        </button>
      </div>
    </div>,
    document.body,
  );
}
