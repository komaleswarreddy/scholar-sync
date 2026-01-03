/**
 * Chat Input Component
 * 
 * Input field for sending messages.
 * Uses placeholder functionality until API keys are added.
 */

'use client';

import { useState, KeyboardEvent } from 'react';
import { Send } from 'lucide-react';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';

interface ChatInputProps {
  onSend?: (message: string, activeSourceIds?: string[]) => void;
  disabled?: boolean;
  activeSourceIds?: string[];
}

export function ChatInput({ onSend, disabled = false, activeSourceIds = [] }: ChatInputProps) {
  const [message, setMessage] = useState('');

  const handleSend = () => {
    if (message.trim() && !disabled) {
      if (onSend) {
        console.log('ChatInput - Sending message with activeSourceIds:', activeSourceIds);
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
      {/* Suggested Prompts */}
      <div className="flex flex-wrap gap-2 mb-4">
        <button
          className="px-4 py-2 text-xs bg-surface border border-border-default rounded-full text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors"
          onClick={() => setMessage('Describe the primary objective of the Pre-Define stage.')}
        >
          Describe the primary objective of the Pre-Define stage.
        </button>
        <button
          className="px-4 py-2 text-xs bg-surface border border-border-default rounded-full text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors"
          onClick={() => setMessage('List three tools used to assess the Voice of Customer.')}
        >
          List three tools used to assess the Voice of Customer.
        </button>
        <button
          className="px-4 py-2 text-xs bg-surface border border-border-default rounded-full text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors"
          onClick={() => setMessage('Explain the role of the PDSA model during improvement.')}
        >
          Explain the role of the PDSA model during improvement.
        </button>
      </div>
      
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
          {disabled ? 'Configure API keys to enable chat' : '1 source'}
        </p>
        <p className="text-xs text-text-tertiary italic">
          NotebookLM can be inaccurate; please double check its responses.
        </p>
      </div>
    </div>
  );
}

