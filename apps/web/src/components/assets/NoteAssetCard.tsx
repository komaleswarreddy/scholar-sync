'use client';

import { FileText, Pin } from 'lucide-react';
import type { StudyNote } from '@/lib/assets-mock-data';
import { AssetCardMenu } from './AssetCardMenu';

type NoteAssetCardProps = {
  note: StudyNote;
  isPinned?: boolean;
  onOpen?: () => void;
  onPin: () => void;
  onEdit: () => void;
  onDelete: () => void;
};

export function NoteAssetCard({
  note,
  isPinned = false,
  onOpen,
  onPin,
  onEdit,
  onDelete,
}: NoteAssetCardProps) {
  return (
    <article
      className={`assets-note-card relative ${isPinned ? 'assets-note-card--pinned' : ''} ${onOpen ? 'cursor-pointer' : ''}`}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (onOpen && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onOpen();
        }
      }}
      role={onOpen ? 'button' : undefined}
      tabIndex={onOpen ? 0 : undefined}
    >
      <div className="absolute top-3 right-3 z-10 flex items-center gap-1">
        {isPinned && (
          <span className="assets-pinned-badge" title="Pinned" aria-label="Pinned note">
            <Pin className="w-3 h-3" fill="currentColor" />
          </span>
        )}
        <AssetCardMenu
          isPinned={isPinned}
          onPin={onPin}
          onEdit={onEdit}
          onDelete={onDelete}
          menuLabel={`Options for ${note.title}`}
        />
      </div>

      <div className="flex gap-4">
        <div className="assets-note-icon flex-shrink-0">
          <FileText className="w-5 h-5 text-[#CA8A04]" strokeWidth={1.75} />
        </div>
        <div className="min-w-0 flex-1 pr-14">
          <h3 className="text-[15px] font-bold text-[var(--color-home-text)] leading-snug">
            {note.title}
          </h3>
          <p className="text-[12px] text-[var(--color-home-text-muted)] mt-1">
            {note.notebook} • {note.subject} • {note.classLevel}
          </p>
          <p className="text-[13px] text-[var(--color-home-text-muted)] mt-2.5 leading-relaxed line-clamp-2">
            {note.snippet}
          </p>
          <p className="text-[11px] text-[var(--color-home-label)] mt-2">{note.timestamp}</p>
        </div>
      </div>
    </article>
  );
}
