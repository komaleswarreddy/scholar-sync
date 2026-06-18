'use client';

import {
  FileText,
  Headphones,
  HelpCircle,
  Layers,
  Network,
  Pin,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import {
  ASSET_TYPE_THEME,
  type AssetType,
  type StudyAsset,
} from '@/lib/assets-mock-data';
import { AssetCardMenu } from './AssetCardMenu';

const typeIcons: Record<AssetType, LucideIcon> = {
  Quiz: HelpCircle,
  Flashcards: Layers,
  'Mind Map': Network,
  Audio: Headphones,
  Summary: FileText,
};

type StudyAssetCardProps = {
  asset: StudyAsset;
  isPinned?: boolean;
  onOpen?: () => void;
  onPin: () => void;
  onEdit: () => void;
  onDelete: () => void;
};

export function StudyAssetCard({
  asset,
  isPinned = false,
  onOpen,
  onPin,
  onEdit,
  onDelete,
}: StudyAssetCardProps) {
  const theme = ASSET_TYPE_THEME[asset.type as AssetType] ?? ASSET_TYPE_THEME.Summary;
  const Icon = typeIcons[asset.type as AssetType] ?? FileText;

  return (
    <article
      className={`assets-study-card relative ${isPinned ? 'assets-study-card--pinned' : ''} ${onOpen ? 'cursor-pointer' : ''}`}
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
          <span
            className="assets-pinned-badge"
            title="Pinned"
            aria-label="Pinned asset"
          >
            <Pin className="w-3 h-3" fill="currentColor" />
          </span>
        )}
        <AssetCardMenu
          isPinned={isPinned}
          onPin={onPin}
          onEdit={onEdit}
          onDelete={onDelete}
          menuLabel={`Options for ${asset.title}`}
        />
      </div>

      <div
        className="assets-study-card-icon"
        style={{ backgroundColor: theme.iconBg, color: theme.iconColor }}
      >
        <Icon className="w-5 h-5" strokeWidth={1.75} />
      </div>

      <p className="text-[11px] font-bold uppercase tracking-wide mt-3" style={{ color: theme.iconColor }}>
        {asset.type}
      </p>
      <h3 className="text-[15px] font-bold text-[var(--color-home-text)] mt-1 leading-snug pr-14">
        {asset.title}
      </h3>
      <p className="text-[12px] text-[var(--color-home-text-muted)] mt-1.5">
        {asset.notebook} • {asset.subject} • {asset.classLevel}
      </p>
      <p className="text-[12px] font-medium text-[var(--color-home-text)] mt-2">{asset.meta}</p>
      <p className="text-[11px] text-[var(--color-home-label)] mt-3">{asset.timestamp}</p>
    </article>
  );
}
