/**
 * Chat Message Component
 * 
 * Displays individual chat messages with citations.
 * Uses placeholder data until API keys are added.
 */

import { MessageCircle, User, Bookmark, ThumbsUp, ThumbsDown } from 'lucide-react';

interface Citation {
  id: string;
  sourceId: string;
  sourceTitle: string;
  text: string;
}

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  timestamp?: string;
}

export function ChatMessage({ role, content, citations = [], timestamp }: ChatMessageProps) {
  // Parse citations in content (format: [1], [2], etc.)
  const renderContentWithCitations = () => {
    const parts = content.split(/(\[\d+\])/g);
    
    return parts.map((part, index) => {
      if (part.match(/\[\d+\]/)) {
        const citationNum = parseInt(part.replace(/[\[\]]/g, ''));
        const citation = citations[citationNum - 1];
        
        return (
          <span key={index}>
            <span
              className="
                bg-citation-badge 
                text-[#E3E3E3] 
                px-1.5 
                rounded 
                text-xs 
                cursor-pointer
                hover:bg-surface-hover
                transition-colors
                align-super
              "
              title={citation ? `Source: ${citation.sourceTitle}` : ''}
            >
              {part}
            </span>
          </span>
        );
      }
      return <span key={index}>{part}</span>;
    });
  };

  if (role === 'user') {
    return (
      <div className="flex items-start gap-3 p-4">
        <div className="w-8 h-8 rounded-full bg-surface flex items-center justify-center flex-shrink-0">
          <User className="w-4 h-4 text-text-secondary" />
        </div>
        <div className="flex-1">
          <p className="text-base text-text-primary leading-relaxed">{content}</p>
          {timestamp && (
            <p className="text-xs text-text-tertiary mt-1">{timestamp}</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 p-4">
      <div className="w-8 h-8 rounded-full bg-surface flex items-center justify-center flex-shrink-0">
        <MessageCircle className="w-4 h-4 text-accent-blue" />
      </div>
      <div className="flex-1">
        <p className="text-base text-text-primary leading-relaxed">
          {renderContentWithCitations()}
        </p>
        {citations.length > 0 && (
          <div className="mt-3 space-y-1">
            {citations.map((citation, index) => (
              <div
                key={citation.id}
                className="text-xs text-text-secondary border-l-2 border-border-default pl-2"
              >
                <span className="text-accent-blue">[{index + 1}]</span>{' '}
                {citation.sourceTitle}: {citation.text}
              </div>
            ))}
          </div>
        )}
        
        {/* Action Buttons */}
        <div className="flex items-center gap-3 mt-3">
          <button className="flex items-center gap-2 px-3 py-1.5 text-xs bg-surface border border-border-default rounded-full text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors">
            <Bookmark className="w-3 h-3" />
            Save to note
          </button>
          <button className="p-1.5 rounded-full hover:bg-surface-hover transition-colors">
            <ThumbsUp className="w-4 h-4 text-text-secondary" />
          </button>
          <button className="p-1.5 rounded-full hover:bg-surface-hover transition-colors">
            <ThumbsDown className="w-4 h-4 text-text-secondary" />
          </button>
        </div>
        
        {timestamp && (
          <p className="text-xs text-text-tertiary mt-2">{timestamp}</p>
        )}
      </div>
    </div>
  );
}

