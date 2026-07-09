'use client';

import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useStudioGenerationSafe } from '@/contexts/StudioGenerationContext';
import { useNotebookContext, useNotebookScopeId } from '@/contexts/NotebookContext';
import { useCreateNote, noteKeys, useNotes, useUpdateNote } from '@/hooks/useNotes';
import { useQueryClient } from '@tanstack/react-query';
import { useAppToast } from '@/contexts/AppToastContext';
import {
  NOTEBOOK_STUDIO_TOOLS,
  PROBLEM_SOLVER_SELECTION_STUDIO_TOOLS,
} from '@/lib/notebook-studio-tools';
import { NOTEBOOK_STUDIO_TONE_STYLES } from '@/lib/notebook-ui-tokens';
import { buildAppendedNoteContent } from '@/components/notes/NoteCreateOrAppendMenu';
import { notePreviewTitle } from '@/lib/note-content';
import { useValidSelectedSourceIds } from '@/hooks/useValidSelectedSourceIds';
import { useOptionalTutorNoteEditor } from '@/contexts/TutorNoteEditorContext';
import {
  EXPLORATORY_STUDIO_SELECTION_BLOCKED_MESSAGE,
  notebookModeRequiresUploadedSources,
} from '@/lib/exploratory-studio';

const SELECTION_INSTRUCTION =
  'Use only the excerpt below as factual context. Do not rely on other chat or documents. ' +
  'When the notebook has no uploaded sources selected, Studio generation is not available.';

const MIN_SELECTION_LENGTH = 15;
const EDGE_PAD = 12;
const SELECTION_GAP = 10;

type SelectionRect = {
  top: number;
  bottom: number;
  left: number;
  right: number;
  centerX: number;
};

type SelectionState = {
  text: string;
  rect: SelectionRect;
};

type PopoverBox = {
  top: number;
  left: number;
};

type Props = {
  scrollContainerRef: React.RefObject<HTMLElement | null>;
};

type Region = {
  top: number;
  left: number;
  right: number;
  bottom: number;
  width: number;
  height: number;
};

function getVisibleRegion(container: HTMLElement): Region {
  const bounds = container.getBoundingClientRect();
  const top = bounds.top + EDGE_PAD;
  const left = bounds.left + EDGE_PAD;
  const right = bounds.right - EDGE_PAD;
  const bottom = bounds.bottom - EDGE_PAD;
  return {
    top,
    left,
    right,
    bottom,
    width: Math.max(0, right - left),
    height: Math.max(0, bottom - top),
  };
}

function clampBox(box: PopoverBox, popW: number, popH: number, region: Region): PopoverBox {
  let { top, left } = box;
  left = Math.max(region.left, Math.min(left, region.right - popW));
  top = Math.max(region.top, Math.min(top, region.bottom - popH));
  return { top, left };
}

/**
 * Prefer centered on selection, slightly above. Flip below if needed, then clamp
 * so the popover never leaves the chat scroll viewport.
 */
function computePopoverBox(
  container: HTMLElement,
  popoverEl: HTMLElement,
  rect: SelectionRect
): PopoverBox {
  const region = getVisibleRegion(container);
  const popW = Math.min(popoverEl.offsetWidth, region.width);
  const popH = Math.min(popoverEl.offsetHeight, region.height);

  if (region.width <= 0 || region.height <= 0) {
    return { top: rect.top, left: rect.centerX - popW / 2 };
  }

  // Horizontally center on selection, then clamp into region.
  let left = rect.centerX - popW / 2;

  // Ideal: sit just above the highlighted text.
  let top = rect.top - SELECTION_GAP - popH;

  // If it doesn't fit above, place just below the selection.
  if (top < region.top) {
    const belowTop = rect.bottom + SELECTION_GAP;
    if (belowTop + popH <= region.bottom) {
      top = belowTop;
    }
  }

  // If still overflowing (tall popover / selection near edge), center in the chat pane.
  if (top < region.top || top + popH > region.bottom) {
    top = region.top + Math.max(0, (region.height - popH) / 2);
  }

  // If horizontal center on selection overflows, center in chat pane.
  if (left < region.left || left + popW > region.right) {
    left = region.left + Math.max(0, (region.width - popW) / 2);
  }

  return clampBox({ top, left }, popW, popH, region);
}

export function NotebookChatSelectionPopover({ scrollContainerRef }: Props) {
  const gen = useStudioGenerationSafe();
  const { notebook } = useNotebookContext();
  const { validSelectedCount } = useValidSelectedSourceIds();
  const exploratoryStudioBlocked =
    notebookModeRequiresUploadedSources(notebook.mode) && validSelectedCount === 0;
  const notebookId = useNotebookScopeId();
  const studioTools = (
    notebook.mode === 'problem_solver'
      ? PROBLEM_SOLVER_SELECTION_STUDIO_TOOLS
      : NOTEBOOK_STUDIO_TOOLS
  ).filter((tool) => tool.type !== 'mind_map');
  const createNote = useCreateNote(notebookId);
  const updateNote = useUpdateNote();
  const { data: notes = [] } = useNotes(notebookId);
  const noteEditor = useOptionalTutorNoteEditor();
  const queryClient = useQueryClient();
  const { showToast } = useAppToast();

  const popoverRef = useRef<HTMLDivElement>(null);
  const selectionRef = useRef<SelectionState | null>(null);
  const [selection, setSelection] = useState<SelectionState | null>(null);
  const [studioMenuOpen, setStudioMenuOpen] = useState(false);
  const [noteMenuOpen, setNoteMenuOpen] = useState(false);
  const [savingNote, setSavingNote] = useState(false);
  const [appendingNoteId, setAppendingNoteId] = useState<string | null>(null);
  const [box, setBox] = useState<PopoverBox | null>(null);
  const [positioned, setPositioned] = useState(false);

  selectionRef.current = selection;

  const closeAll = useCallback(() => {
    setSelection(null);
    setStudioMenuOpen(false);
    setNoteMenuOpen(false);
    setAppendingNoteId(null);
    setBox(null);
    setPositioned(false);
  }, []);

  const menuExpanded = noteMenuOpen || studioMenuOpen;

  const refreshSelectionRect = useCallback(() => {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0 || !selectionRef.current) return;

    const range = sel.getRangeAt(0);
    const text = sel.toString().trim();
    if (text.length < MIN_SELECTION_LENGTH) return;

    const rect = range.getBoundingClientRect();
    if (rect.width < 1 && rect.height < 1) return;

    const nextRect: SelectionRect = {
      top: rect.top,
      bottom: rect.bottom,
      left: rect.left,
      right: rect.right,
      centerX: rect.left + rect.width / 2,
    };

    selectionRef.current = { ...selectionRef.current, rect: nextRect };
    setSelection(selectionRef.current);
  }, []);

  const updatePosition = useCallback(() => {
    const container = scrollContainerRef.current;
    const popoverEl = popoverRef.current;
    const currentSelection = selectionRef.current;
    if (!container || !popoverEl || !currentSelection) return;

    setBox(computePopoverBox(container, popoverEl, currentSelection.rect));
    setPositioned(true);
  }, [scrollContainerRef]);

  useLayoutEffect(() => {
    setPositioned(false);
    updatePosition();
    const id = requestAnimationFrame(() => updatePosition());
    return () => cancelAnimationFrame(id);
  }, [updatePosition, menuExpanded, selection]);

  useEffect(() => {
    const container = scrollContainerRef.current;
    const popoverEl = popoverRef.current;
    if (!container || !popoverEl || !selection) return;

    const ro = new ResizeObserver(() => updatePosition());
    ro.observe(popoverEl);

    const onScrollOrResize = () => {
      refreshSelectionRect();
      updatePosition();
    };
    container.addEventListener('scroll', onScrollOrResize, { passive: true });
    window.addEventListener('resize', onScrollOrResize);

    return () => {
      ro.disconnect();
      container.removeEventListener('scroll', onScrollOrResize);
      window.removeEventListener('resize', onScrollOrResize);
    };
  }, [scrollContainerRef, selection, updatePosition, refreshSelectionRect]);

  useEffect(() => {
    const onDocMouseDown = (e: MouseEvent) => {
      const t = e.target as Node;
      if (popoverRef.current?.contains(t)) return;
      closeAll();
    };

    document.addEventListener('mousedown', onDocMouseDown);
    return () => document.removeEventListener('mousedown', onDocMouseDown);
  }, [closeAll]);

  useEffect(() => {
    const el = scrollContainerRef.current;
    if (!el) return;

    const onMouseUp = () => {
      const sel = window.getSelection();
      if (!sel || sel.rangeCount === 0) return;

      const text = sel.toString().trim();
      if (text.length < MIN_SELECTION_LENGTH) return;

      const range = sel.getRangeAt(0);
      let node: Node | null = range.commonAncestorContainer;
      if (node.nodeType === Node.TEXT_NODE) {
        node = node.parentElement;
      }
      if (!node || !(node instanceof Element) || !el.contains(node)) return;

      const assistantContent = node.closest('[data-assistant-content]');
      if (!assistantContent || !el.contains(assistantContent)) return;

      const rect = range.getBoundingClientRect();
      if (rect.width < 1 && rect.height < 1) return;

      setStudioMenuOpen(false);
      setNoteMenuOpen(false);
      setPositioned(false);
      setSelection({
        text,
        rect: {
          top: rect.top,
          bottom: rect.bottom,
          left: rect.left,
          right: rect.right,
          centerX: rect.left + rect.width / 2,
        },
      });
    };

    el.addEventListener('mouseup', onMouseUp);
    return () => el.removeEventListener('mouseup', onMouseUp);
  }, [scrollContainerRef]);

  const handleCreateNote = async () => {
    if (!selection || savingNote) return;
    setSavingNote(true);
    try {
      await createNote.mutateAsync({ content: selection.text });
      if (notebookId) {
        queryClient.invalidateQueries({ queryKey: noteKeys.list(notebookId) });
      }
      window.dispatchEvent(new CustomEvent('noteCreated'));
      showToast('Saved to Notes');
      window.getSelection()?.removeAllRanges();
      closeAll();
    } catch {
      showToast('Could not save note');
    } finally {
      setSavingNote(false);
    }
  };

  const handleAppendToNote = async (noteId: string, content: string) => {
    const existing = notes.find((note) => note.id === noteId);
    if (!existing || appendingNoteId) return;
    setAppendingNoteId(noteId);
    setSavingNote(true);
    try {
      const nextContent = await buildAppendedNoteContent(existing.content, content);
      await updateNote.mutateAsync({ noteId, content: nextContent });
      if (notebookId) {
        queryClient.invalidateQueries({ queryKey: noteKeys.list(notebookId) });
      }
      window.dispatchEvent(new CustomEvent('noteCreated'));
      showToast(`Added to ${notePreviewTitle(existing.content)}`);
      noteEditor?.setActiveNote(noteId);
      window.getSelection()?.removeAllRanges();
      closeAll();
    } catch {
      showToast('Could not append to note');
    } finally {
      setSavingNote(false);
      setAppendingNoteId(null);
    }
  };

  const handleGenerateStudio = (taskType: string) => {
    if (!gen || !selection || exploratoryStudioBlocked) return;
    const t = selection.text;
    closeAll();
    window.getSelection()?.removeAllRanges();
    void gen.generate({
      taskType,
      sourceIds: [],
      contextMode: 'selection_only',
      selectionText: t,
      instructions: SELECTION_INSTRUCTION,
    });
  };

  if (!selection) return null;

  const isGenerating = Boolean(gen?.generating || gen?.loading);
  const fallback = computeFallbackBox(selection.rect);

  return (
    <div
      ref={popoverRef}
      id="notebook-chat-selection-popover"
      className={`notebook-selection-popover-root${
        menuExpanded ? ' notebook-selection-popover-root--expanded' : ''
      }`}
      style={{
        visibility: positioned ? 'visible' : 'hidden',
        top: box?.top ?? fallback.top,
        left: box?.left ?? fallback.left,
      }}
      role="menu"
      aria-label="Selection actions"
      onMouseDown={(e) => e.stopPropagation()}
    >
      <div
        className={`notebook-selection-popover${
          menuExpanded ? '' : ' notebook-selection-popover--compact'
        }`}
      >
        <div className="notebook-selection-popover-actions">
          {notes.length >= 1 ? (
            <button
              type="button"
              role="menuitem"
              className={`notebook-selection-popover-btn${
                noteMenuOpen ? ' notebook-selection-popover-btn--active' : ''
              }`}
              disabled={savingNote}
              onClick={() => {
                setStudioMenuOpen(false);
                setNoteMenuOpen((open) => !open);
              }}
              aria-expanded={noteMenuOpen}
              aria-haspopup="menu"
            >
              {savingNote ? 'Saving…' : 'Create Note'}
            </button>
          ) : (
            <button
              type="button"
              role="menuitem"
              className="notebook-selection-popover-btn"
              disabled={savingNote}
              onClick={() => void handleCreateNote()}
            >
              {savingNote ? 'Saving…' : 'Create Note'}
            </button>
          )}
          <button
            type="button"
            role="menuitem"
            className={`notebook-selection-popover-btn${
              studioMenuOpen ? ' notebook-selection-popover-btn--active' : ''
            }`}
            disabled={!gen || isGenerating || exploratoryStudioBlocked}
            title={
              exploratoryStudioBlocked
                ? EXPLORATORY_STUDIO_SELECTION_BLOCKED_MESSAGE
                : undefined
            }
            onClick={() => {
              if (exploratoryStudioBlocked) return;
              setNoteMenuOpen(false);
              setStudioMenuOpen((open) => !open);
            }}
            aria-expanded={studioMenuOpen}
          >
            Generate Studio
          </button>
        </div>

        {noteMenuOpen && notes.length >= 1 && (
          <div
            id="notebook-chat-selection-note-menu"
            className="notebook-selection-note-panel"
            role="menu"
            aria-label="Save selection to notes"
          >
            <p className="notebook-selection-studio-menu-title">Save to Notes</p>
            <button
              type="button"
              role="menuitem"
              className="notebook-selection-note-item notebook-selection-note-item--primary"
              disabled={savingNote}
              onClick={() => void handleCreateNote()}
            >
              {savingNote && !appendingNoteId ? 'Saving…' : 'Create new note'}
            </button>
            {selection.text.trim().length > 0 && (
              <>
                <p className="notebook-selection-note-menu-label">Append to…</p>
                <div className="notebook-selection-note-list">
                  {notes.slice(0, 8).map((note) => (
                    <button
                      key={note.id}
                      type="button"
                      role="menuitem"
                      className="notebook-selection-note-item"
                      disabled={savingNote}
                      onClick={() => void handleAppendToNote(note.id, selection.text)}
                    >
                      {appendingNoteId === note.id
                        ? 'Adding…'
                        : notePreviewTitle(note.content)}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {studioMenuOpen && !exploratoryStudioBlocked && (
          <div
            id="notebook-chat-selection-studio-menu"
            className="notebook-selection-studio-panel"
          >
            <p className="notebook-selection-studio-menu-title">Generate from selection</p>
            <div className="notebook-selection-studio-grid">
              {studioTools.map(({ type, title, icon: Icon, tone }) => {
                const toneStyle = NOTEBOOK_STUDIO_TONE_STYLES[tone];
                return (
                  <button
                    key={type}
                    type="button"
                    role="menuitem"
                    disabled={!gen || isGenerating}
                    className="notebook-selection-studio-item"
                    onClick={() => handleGenerateStudio(type)}
                  >
                    <span
                      className="notebook-selection-studio-icon"
                      style={{ backgroundColor: toneStyle.bg, color: toneStyle.color }}
                    >
                      <Icon className="w-3.5 h-3.5" strokeWidth={2} />
                    </span>
                    <span className="notebook-selection-studio-item-label">{title}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function computeFallbackBox(rect: SelectionRect): PopoverBox {
  return {
    top: Math.max(EDGE_PAD, rect.top - SELECTION_GAP - 40),
    left: rect.centerX - 100,
  };
}
