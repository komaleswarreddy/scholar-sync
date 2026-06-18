'use client';

import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import Link from '@tiptap/extension-link';
import Placeholder from '@tiptap/extension-placeholder';
import { EditorContent, useEditor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import {
  ArrowLeft,
  Bold,
  ChevronDown,
  Code,
  Italic,
  Link2,
  List,
  ListOrdered,
  Quote,
  Redo2,
  Trash2,
  Undo2,
} from 'lucide-react';
import { useNotebookScopeId } from '@/contexts/NotebookContext';
import { useAppToast } from '@/contexts/AppToastContext';
import {
  useCreateNote,
  useDeleteNote,
  useNote,
  useUpdateNote,
} from '@/hooks/useNotes';
import { parseNoteContent, serializeNoteContent } from '@/lib/note-content';

interface NoteRichEditorProps {
  noteId: string | null;
  onClose: () => void;
}

type BlockStyle = 'paragraph' | 'h2' | 'h3';

const AUTOSAVE_MS = 2000;

export function NoteRichEditor({ noteId, onClose }: NoteRichEditorProps) {
  const notebookId = useNotebookScopeId();
  const { showToast } = useAppToast();
  const isNew = !noteId;

  const { data: existingNote, isLoading } = useNote(noteId);
  const createMutation = useCreateNote(notebookId);
  const updateMutation = useUpdateNote();
  const deleteMutation = useDeleteNote();

  const [title, setTitle] = useState('New Note');
  const [savedNoteId, setSavedNoteId] = useState<string | null>(noteId);
  const [blockStyle, setBlockStyle] = useState<BlockStyle>('paragraph');
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latestPayloadRef = useRef({ title: 'New Note', html: '' });
  const isSavingRef = useRef(false);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [2, 3] },
      }),
      Link.configure({
        openOnClick: false,
        HTMLAttributes: { class: 'tutor-note-editor__link' },
      }),
      Placeholder.configure({
        placeholder: 'Start writing…',
      }),
    ],
    content: '',
    editorProps: {
      attributes: {
        class: 'tutor-note-editor__content ProseMirror',
      },
    },
    immediatelyRender: false,
  });

  useEffect(() => {
    if (isNew || !existingNote) return;
    const parsed = parseNoteContent(existingNote.content);
    setTitle(parsed.title);
    editor?.commands.setContent(parsed.bodyHtml || '<p></p>');
  }, [existingNote, isNew, editor]);

  const persistNote = useCallback(async () => {
    if (isSavingRef.current) return;
    const { title: nextTitle, html } = latestPayloadRef.current;
    const content = serializeNoteContent(nextTitle, html);
    if (!content.trim()) return;

    isSavingRef.current = true;
    try {
      if (savedNoteId) {
        await updateMutation.mutateAsync({ noteId: savedNoteId, content });
      } else {
        const created = await createMutation.mutateAsync({ content });
        if (created?.id) setSavedNoteId(created.id);
      }
    } catch {
      showToast('Could not save note');
    } finally {
      isSavingRef.current = false;
    }
  }, [createMutation, savedNoteId, showToast, updateMutation]);

  const scheduleSave = useCallback(() => {
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => {
      void persistNote();
    }, AUTOSAVE_MS);
  }, [persistNote]);

  useEffect(() => {
    if (!editor) return;
    const onUpdate = () => {
      latestPayloadRef.current = {
        title,
        html: editor.getHTML(),
      };
      scheduleSave();
    };
    editor.on('update', onUpdate);
    return () => {
      editor.off('update', onUpdate);
    };
  }, [editor, scheduleSave, title]);

  useEffect(() => {
    latestPayloadRef.current = {
      title,
      html: editor?.getHTML() ?? '',
    };
    scheduleSave();
  }, [title, editor, scheduleSave]);

  useEffect(
    () => () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    },
    [],
  );

  const handleClose = async () => {
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    await persistNote();
    onClose();
  };

  const handleDelete = async () => {
    if (!savedNoteId) {
      onClose();
      return;
    }
    const confirmed = window.confirm('Delete this note? This cannot be undone.');
    if (!confirmed) return;
    try {
      await deleteMutation.mutateAsync(savedNoteId);
      onClose();
    } catch {
      showToast('Could not delete note');
    }
  };

  const setLink = () => {
    if (!editor) return;
    const previous = editor.getAttributes('link').href as string | undefined;
    const url = window.prompt('Enter URL', previous || 'https://');
    if (url === null) return;
    if (url === '') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run();
      return;
    }
    editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run();
  };

  const applyBlockStyle = (style: BlockStyle) => {
    if (!editor) return;
    setBlockStyle(style);
    if (style === 'paragraph') {
      editor.chain().focus().setParagraph().run();
    } else if (style === 'h2') {
      editor.chain().focus().toggleHeading({ level: 2 }).run();
    } else {
      editor.chain().focus().toggleHeading({ level: 3 }).run();
    }
  };

  if (!editor) return null;

  if (!isNew && isLoading) {
    return (
      <div className="tutor-note-editor flex flex-col h-full items-center justify-center text-[var(--color-home-text-muted)]">
        Loading note…
      </div>
    );
  }

  return (
    <div className="tutor-note-editor flex flex-col h-full min-h-0 w-full flex-1">
      <div className="tutor-note-editor__topbar flex items-center justify-between px-4 py-2.5">
        <button
          type="button"
          className="tutor-note-editor__back inline-flex items-center gap-1.5 text-[12px] font-semibold"
          onClick={() => void handleClose()}
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back
        </button>
        <span className="tutor-note-editor__breadcrumb text-[11px] font-medium tracking-wide">
          Studio › Note
        </span>
        <span className="w-12" aria-hidden />
      </div>

      <div className="tutor-note-editor__title-row flex items-center justify-between gap-3 px-4 py-3">
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="tutor-note-editor__title flex-1 min-w-0 bg-transparent outline-none placeholder:text-[var(--color-home-text-muted)]"
          placeholder="New Note"
          aria-label="Note title"
        />
        <button
          type="button"
          className="tutor-note-editor__delete-btn"
          onClick={() => void handleDelete()}
          aria-label="Delete note"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      <div className="tutor-note-editor__toolbar flex flex-nowrap items-center gap-0.5 px-3 py-2 overflow-x-auto">
        <ToolbarButton onClick={() => editor.chain().focus().undo().run()} label="Undo">
          <Undo2 className="w-4 h-4" />
        </ToolbarButton>
        <ToolbarButton onClick={() => editor.chain().focus().redo().run()} label="Redo">
          <Redo2 className="w-4 h-4" />
        </ToolbarButton>
        <ToolbarDivider />

        <div className="relative">
          <button
            type="button"
            tabIndex={-1}
            className="tutor-note-editor__select inline-flex items-center gap-1 px-2 py-1.5 text-[12px] font-medium text-[var(--color-home-text)] rounded-lg pointer-events-none"
          >
            {blockStyle === 'paragraph' ? 'Normal' : blockStyle === 'h2' ? 'Heading 2' : 'Heading 3'}
            <ChevronDown className="w-3 h-3" />
          </button>
          <select
            className="absolute inset-0 opacity-0 cursor-pointer"
            value={blockStyle}
            onChange={(e) => applyBlockStyle(e.target.value as BlockStyle)}
            aria-label="Text style"
          >
            <option value="paragraph">Normal</option>
            <option value="h2">Heading 2</option>
            <option value="h3">Heading 3</option>
          </select>
        </div>

        <ToolbarDivider />
        <ToolbarButton
          active={editor.isActive('bold')}
          onClick={() => editor.chain().focus().toggleBold().run()}
          label="Bold"
        >
          <Bold className="w-4 h-4" />
        </ToolbarButton>
        <ToolbarButton
          active={editor.isActive('italic')}
          onClick={() => editor.chain().focus().toggleItalic().run()}
          label="Italic"
        >
          <Italic className="w-4 h-4" />
        </ToolbarButton>
        <ToolbarDivider />
        <ToolbarButton onClick={setLink} active={editor.isActive('link')} label="Link">
          <Link2 className="w-4 h-4" />
        </ToolbarButton>
        <ToolbarButton
          active={editor.isActive('code')}
          onClick={() => editor.chain().focus().toggleCode().run()}
          label="Inline code"
        >
          <Code className="w-4 h-4" />
        </ToolbarButton>
        <ToolbarButton
          active={editor.isActive('codeBlock')}
          onClick={() => editor.chain().focus().toggleCodeBlock().run()}
          label="Code block"
        >
          <span className="text-[11px] font-bold">&lt;/&gt;</span>
        </ToolbarButton>
        <ToolbarDivider />
        <ToolbarButton
          active={editor.isActive('bulletList')}
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          label="Bullet list"
        >
          <List className="w-4 h-4" />
        </ToolbarButton>
        <ToolbarButton
          active={editor.isActive('orderedList')}
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          label="Numbered list"
        >
          <ListOrdered className="w-4 h-4" />
        </ToolbarButton>
        <ToolbarButton
          active={editor.isActive('blockquote')}
          onClick={() => editor.chain().focus().toggleBlockquote().run()}
          label="Blockquote"
        >
          <Quote className="w-4 h-4" />
        </ToolbarButton>
      </div>

      <div className="tutor-note-editor__body-wrap flex-1 min-h-0 overflow-y-auto">
        <EditorContent editor={editor} className="tutor-note-editor__body h-full" />
      </div>
    </div>
  );
}

function ToolbarButton({
  children,
  onClick,
  label,
  active = false,
}: {
  children: ReactNode;
  onClick: () => void;
  label: string;
  active?: boolean;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      onClick={onClick}
      className={`tutor-note-editor__icon-btn ${active ? 'tutor-note-editor__icon-btn--active' : ''}`}
    >
      {children}
    </button>
  );
}

function ToolbarDivider() {
  return <span className="tutor-note-editor__divider" aria-hidden />;
}
