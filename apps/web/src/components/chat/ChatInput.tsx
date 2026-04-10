/**
 * Chat Input Component
 * 
 * Input field for sending messages.
 * Uses placeholder functionality until API keys are added.
 */

'use client';

import { useState, KeyboardEvent, useMemo } from 'react';
import { Send } from 'lucide-react';
import { Input } from '../ui/Input';
import { useSources } from '@/hooks/useSources';
import { normalizeSourceId } from '@/hooks/useValidSelectedSourceIds';

interface ChatInputProps {
  onSend?: (message: string, activeSourceIds?: string[]) => void;
  disabled?: boolean;
  activeSourceIds?: string[];
  /** When false, starter suggestion chips are hidden (after first user message in this chat). */
  showSuggestedPrompts?: boolean;
  helperText?: string;
  disabledReason?: string | null;
}

export function ChatInput({
  onSend,
  disabled = false,
  activeSourceIds = [],
  showSuggestedPrompts = true,
  helperText,
  disabledReason,
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const { data: sources = [] } = useSources();
  
  // Get selected source titles for generating relevant prompts
  const selectedSources = useMemo(() => {
    if (activeSourceIds.length === 0) return [];
    return sources.filter((source) =>
      activeSourceIds.some((aid) => normalizeSourceId(aid) === normalizeSourceId(source.id))
    );
  }, [sources, activeSourceIds]);
  
  // Generate dynamic prompts based on selected sources
  const suggestedPrompts = useMemo(() => {
    if (selectedSources.length === 0) {
      // Generic prompts when no sources selected
      return [
        'What are the main topics covered in this document?',
        'Summarize the key points.',
        'What questions does this document answer?'
      ];
    }
    
    // Generate contextual prompts based on source titles
    const sourceContext = selectedSources.length === 1 
      ? `this document${selectedSources[0].title ? ` (${selectedSources[0].title})` : ''}`
      : 'these documents';
    
    return [
      `What are the main topics covered in ${sourceContext}?`,
      `Summarize the key points from ${sourceContext}.`,
      `What are the most important concepts in ${sourceContext}?`,
      `Explain the main ideas discussed in ${sourceContext}.`,
      `What questions does ${sourceContext} answer?`
    ];
  }, [selectedSources]);

  const handleSend = () => {
    if (message.trim() && !disabled) {
      if (onSend) {
        onSend(message, activeSourceIds);
      }
      setMessage('');
    }
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="p-4">
      {/* Suggested Prompts - only before the first user message in this chat */}
      {showSuggestedPrompts && suggestedPrompts.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {suggestedPrompts.slice(0, 3).map((prompt, index) => (
            <button
              key={index}
              className="px-4 py-2 text-xs bg-surface border border-border-default rounded-full text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={() => setMessage(prompt)}
              disabled={disabled}
            >
              {prompt}
            </button>
          ))}
        </div>
      )}
      
      {/* Floating Input Bar */}
      <div className="flex items-center gap-2 bg-surface border border-border-default rounded-full px-4 py-2">
        <Input
          type="text"
          placeholder="Start typing..."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={disabled}
          className="border-0 bg-transparent focus:ring-0"
        />
        <button
          onClick={handleSend}
          disabled={disabled || !message.trim()}
          className="p-2 rounded-full bg-accent-blue text-background hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
          title="Send message"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
      
      <div className="flex items-center justify-between mt-3 px-2">
        <p className="text-xs text-text-tertiary">
          {disabled ? (disabledReason || 'Chat unavailable right now') : (helperText || 'Chat ready')}
        </p>
        <p className="text-xs text-text-tertiary italic">
          NotebookLM can be inaccurate; please double check its responses.
        </p>
      </div>
    </div>
  );
}

