'use client';

import React, { useCallback, useEffect, useState } from 'react';
import {
  FileQuestion,
  Layers,
  Network,
  Presentation,
} from 'lucide-react';
import { useStudioGenerationSafe } from '@/contexts/StudioGenerationContext';

const SELECTION_INSTRUCTION =
  'Use only the excerpt below as factual context. Do not rely on other chat or documents.';

const ACTIONS: {
  type: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}[] = [
  { type: 'mind_map', label: 'Mind Map', icon: Network },
  { type: 'flashcards', label: 'Flashcards', icon: Layers },
  { type: 'quiz', label: 'Quiz', icon: FileQuestion },
  { type: 'slide_deck', label: 'Slide Deck', icon: Presentation },
];

type Props = {
  scrollContainerRef: React.RefObject<HTMLElement | null>;
  enabled: boolean;
};

export function ChatStudioSelectionToolbar({ scrollContainerRef, enabled }: Props) {
  const gen = useStudioGenerationSafe();
  const [menu, setMenu] = useState<{ x: number; y: number; text: string } | null>(null);

  const closeMenu = useCallback(() => setMenu(null), []);

  useEffect(() => {
    if (!enabled || !gen) return;

    const onDocMouseDown = (e: MouseEvent) => {
      const t = e.target as Node;
      const pop = document.getElementById('chat-studio-selection-popover');
      if (pop?.contains(t)) return;
      closeMenu();
    };

    document.addEventListener('mousedown', onDocMouseDown);
    return () => document.removeEventListener('mousedown', onDocMouseDown);
  }, [enabled, gen, closeMenu]);

  useEffect(() => {
    if (!enabled || !gen) return;
    const el = scrollContainerRef.current;
    if (!el) return;

    const onMouseUp = () => {
      const sel = window.getSelection();
      if (!sel || sel.rangeCount === 0) {
        return;
      }
      const text = sel.toString().trim();
      if (text.length < 15) {
        return;
      }
      const range = sel.getRangeAt(0);
      let node: Node | null = range.commonAncestorContainer;
      if (node.nodeType === Node.TEXT_NODE) {
        node = node.parentElement;
      }
      if (!node || !(node instanceof Element) || !el.contains(node)) {
        return;
      }
      const rect = range.getBoundingClientRect();
      if (rect.width < 1 && rect.height < 1) {
        return;
      }
      setMenu({
        x: rect.left + rect.width / 2,
        y: rect.top,
        text,
      });
    };

    el.addEventListener('mouseup', onMouseUp);
    return () => el.removeEventListener('mouseup', onMouseUp);
  }, [enabled, gen, scrollContainerRef]);

  if (!enabled || !gen || !menu) {
    return null;
  }

  return (
    <div
      id="chat-studio-selection-popover"
      className="fixed z-[70] flex flex-col gap-1 rounded-xl border border-border-default bg-surface py-2 px-2 shadow-xl max-w-[min(92vw,280px)]"
      style={{
        left: menu.x,
        top: menu.y,
        transform: 'translate(-50%, calc(-100% - 8px))',
      }}
      role="menu"
      aria-label="Studio actions for selection"
    >
      <p className="text-[10px] text-text-tertiary px-1 pb-1 border-b border-border-default mb-1">
        Studio from selection
      </p>
      <div className="grid grid-cols-2 gap-1">
        {ACTIONS.map(({ type, label, icon: Icon }) => (
          <button
            key={type}
            type="button"
            role="menuitem"
            disabled={gen.generating !== null || gen.loading}
            className="flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-left text-xs text-text-primary hover:bg-surface-hover disabled:opacity-50"
            onClick={() => {
              const t = menu.text;
              closeMenu();
              window.getSelection()?.removeAllRanges();
              void gen.generate({
                taskType: type,
                sourceIds: [],
                contextMode: 'selection_only',
                selectionText: t,
                instructions: SELECTION_INSTRUCTION,
              });
            }}
          >
            <Icon className="w-3.5 h-3.5 shrink-0 text-text-secondary" />
            <span className="truncate">{label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
