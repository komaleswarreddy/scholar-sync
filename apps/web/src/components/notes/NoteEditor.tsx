'use client';

import { useState, useEffect, useRef } from 'react';
import { Save, X } from 'lucide-react';
import { Button } from '../ui/Button';

interface NoteEditorProps {
  initialContent?: string;
  onSave: (content: string) => Promise<void>;
  onCancel: () => void;
  noteId?: string;
}

export function NoteEditor({ initialContent = '', onSave, onCancel, noteId }: NoteEditorProps) {
  const [content, setContent] = useState(initialContent);
  const [isSaving, setIsSaving] = useState(false);
  const [charCount, setCharCount] = useState(initialContent.length);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const draftKeyRef = useRef<string>(noteId ? `note-draft-${noteId}` : 'note-draft-new');
  const isInitialLoadCompleteRef = useRef(false);
  const previousContentRef = useRef<string>(initialContent);

  // Auto-save draft to localStorage
  const DRAFT_KEY = draftKeyRef.current;

  useEffect(() => {
    // Only run on client side
    if (typeof window === 'undefined') return;

    // Load draft from localStorage on mount
    const savedDraft = localStorage.getItem(DRAFT_KEY);
    
    // On initial mount, prioritize draft over initialContent if draft exists
    if (!isInitialLoadCompleteRef.current) {
      if (savedDraft) {
        // If there's a saved draft, use it (user might have been editing)
        setContent(savedDraft);
        setCharCount(savedDraft.length);
        previousContentRef.current = savedDraft;
      } else if (initialContent) {
        // Otherwise use initialContent if provided
        setContent(initialContent);
        setCharCount(initialContent.length);
        previousContentRef.current = initialContent;
      }
      isInitialLoadCompleteRef.current = true;
    }

    // Focus textarea on mount
    if (textareaRef.current) {
      textareaRef.current.focus();
      // Move cursor to end
      const len = textareaRef.current.value.length;
      textareaRef.current.setSelectionRange(len, len);
    }
  }, [DRAFT_KEY, initialContent]);

  useEffect(() => {
    // Only run on client side
    if (typeof window === 'undefined') return;
    
    // Don't save until initial load is complete
    if (!isInitialLoadCompleteRef.current) return;
    
    // Don't save if content hasn't actually changed (avoid saving on mount)
    if (content === previousContentRef.current) return;
    
    // Update previous content
    previousContentRef.current = content;

    // Save draft to localStorage on content change (debounced)
    const timer = setTimeout(() => {
      try {
        if (content.trim()) {
          localStorage.setItem(DRAFT_KEY, content);
          console.log('[NoteEditor] Draft saved to localStorage:', DRAFT_KEY, 'Length:', content.length);
        } else {
          localStorage.removeItem(DRAFT_KEY);
          console.log('[NoteEditor] Draft removed (empty content):', DRAFT_KEY);
        }
      } catch (error) {
        console.error('[NoteEditor] Failed to save draft to localStorage:', error);
      }
    }, 500); // 500ms debounce

    return () => clearTimeout(timer);
  }, [content, DRAFT_KEY]);

  // Save draft immediately when component unmounts
  useEffect(() => {
    return () => {
      if (typeof window === 'undefined') return;
      try {
        if (content.trim()) {
          localStorage.setItem(DRAFT_KEY, content);
          console.log('[NoteEditor] Draft saved on unmount:', DRAFT_KEY);
        }
      } catch (error) {
        console.error('[NoteEditor] Failed to save draft on unmount:', error);
      }
    };
  }, [content, DRAFT_KEY]);

  const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newContent = e.target.value;
    setContent(newContent);
    setCharCount(newContent.length);
  };

  const handleSave = async () => {
    if (!content.trim()) {
      return;
    }

    setIsSaving(true);
    try {
      await onSave(content.trim());
      // Clear draft after successful save
      if (typeof window !== 'undefined') {
        try {
          localStorage.removeItem(DRAFT_KEY);
          console.log('[NoteEditor] Draft cleared after successful save:', DRAFT_KEY);
        } catch (error) {
          console.error('[NoteEditor] Failed to clear draft:', error);
        }
      }
    } catch (error) {
      console.error('Failed to save note:', error);
      // Don't clear draft on error - keep it for retry
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    // Don't clear draft when canceling - user might want to come back to it
    // The draft will be overwritten next time they edit/create
    onCancel();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Ctrl/Cmd + S to save
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      handleSave();
    }
    // Escape to cancel
    if (e.key === 'Escape') {
      handleCancel();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Editor */}
      <div className="flex-1 flex flex-col p-4">
        <textarea
          ref={textareaRef}
          value={content}
          onChange={handleContentChange}
          onKeyDown={handleKeyDown}
          placeholder="Start typing your note..."
          className="flex-1 w-full resize-none bg-transparent text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-0 border-0 p-0 font-mono text-sm leading-relaxed"
          style={{
            minHeight: '200px',
            maxHeight: 'calc(100vh - 200px)',
            overflowY: 'auto',
          }}
        />
      </div>

      {/* Footer with character count and actions */}
      <div className="border-t border-border-default p-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="text-xs text-text-tertiary">
            {charCount.toLocaleString()} {charCount === 1 ? 'character' : 'characters'}
          </span>
          <span className="text-xs text-text-tertiary">
            Press Ctrl+S to save, Esc to cancel
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCancel}
            disabled={isSaving}
            className="text-text-secondary hover:text-text-primary"
          >
            <X className="w-4 h-4 mr-1" />
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleSave}
            disabled={isSaving || !content.trim()}
            className="bg-accent-blue text-background hover:opacity-90"
          >
            <Save className="w-4 h-4 mr-1" />
            {isSaving ? 'Saving...' : 'Save'}
          </Button>
        </div>
      </div>
    </div>
  );
}
