'use client';

import { ChevronRight, Play, NotebookPen, BookOpen, Bookmark, LucideIcon } from 'lucide-react';

type QuickActionTone = 'continue' | 'notebook' | 'library' | 'assets';

type QuickActionCardProps = {
  tone: QuickActionTone;
  title: string;
  description: string;
  onClick?: () => void;
  isActive?: boolean;
};

const toneConfig: Record<
  QuickActionTone,
  {
    variant: 'primary' | 'default';
    Icon: LucideIcon;
    iconWrap: string;
    iconClass: string;
  }
> = {
  continue: {
    variant: 'primary',
    Icon: Play,
    iconWrap: 'bg-white',
    iconClass: 'text-[#0D3D2E] fill-[#0D3D2E]',
  },
  notebook: {
    variant: 'default',
    Icon: NotebookPen,
    iconWrap: 'bg-[#E8F2EE]',
    iconClass: 'text-[#0D3D2E]',
  },
  library: {
    variant: 'default',
    Icon: BookOpen,
    iconWrap: 'bg-[#E8EAF6]',
    iconClass: 'text-[#3D5A80]',
  },
  assets: {
    variant: 'default',
    Icon: Bookmark,
    iconWrap: 'bg-[#FFF4EC]',
    iconClass: 'text-[#EA580C]',
  },
};

export function QuickActionCard({
  tone,
  title,
  description,
  onClick,
  isActive = false,
}: QuickActionCardProps) {
  const { variant, Icon, iconWrap, iconClass } = toneConfig[tone];
  const isPrimary = variant === 'primary';

  return (
    <button
      type="button"
      onClick={onClick}
      aria-expanded={isActive}
      className={[
        isPrimary
          ? 'home-quick-action home-quick-action--primary'
          : 'home-quick-action home-quick-action--default',
        isActive ? 'home-quick-action--active' : '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <div
        className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 ${iconWrap}`}
      >
        <Icon
          className={`w-[18px] h-[18px] ${iconClass}`}
          strokeWidth={isPrimary ? 2 : 1.75}
        />
      </div>
      <div className="flex-1 min-w-0 text-left">
        <p
          className={`text-[14px] font-bold leading-tight truncate ${
            isPrimary ? 'text-white' : 'text-[#1A1F1C]'
          }`}
        >
          {title}
        </p>
        <p
          className={`text-[12px] leading-snug mt-0.5 truncate ${
            isPrimary ? 'text-white/85' : 'text-[#6B7280]'
          }`}
        >
          {description}
        </p>
      </div>
      <ChevronRight
        className={`w-4 h-4 flex-shrink-0 ${
          isPrimary ? 'text-white/90' : 'text-[#9CA3AF]'
        }`}
        strokeWidth={2}
      />
    </button>
  );
}
