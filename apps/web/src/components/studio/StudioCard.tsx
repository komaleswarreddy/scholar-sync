/**
 * Studio Card Component
 * 
 * Individual card for Studio tools (Quiz, Flashcards, etc.).
 * Uses placeholder functionality until API keys are added.
 */

import { ReactNode } from 'react';
import { Edit2 } from 'lucide-react';
import { Card } from '../ui/Card';

interface StudioCardProps {
  icon: ReactNode;
  title: string;
  onClick?: () => void;
  disabled?: boolean;
  /** Shown on hover (e.g. when disabled) */
  disabledHint?: string;
}

export function StudioCard({ icon, title, onClick, disabled = false, disabledHint }: StudioCardProps) {
  const handleClick = () => {
    if (disabled) return;
    if (onClick) {
      onClick();
    }
    // If no onClick is provided, do nothing (should not happen in production)
  };

  return (
    <Card 
      hover={!disabled} 
      onClick={handleClick} 
      className={`h-[88px] relative ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      title={disabled && disabledHint ? disabledHint : undefined}
    >
      {/* Icon - Top Left */}
      <div className="absolute top-3 left-3 w-5 h-5 text-accent-blue">
        {icon}
      </div>
      
      {/* Edit Button - Top Right (shows on hover) */}
      <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          className="p-1 rounded hover:bg-surface text-text-secondary hover:text-text-primary"
          onClick={(e) => {
            e.stopPropagation();
            // TODO: Open edit modal
          }}
        >
          <Edit2 className="w-4 h-4" />
        </button>
      </div>
      
      {/* Title - Bottom Left */}
      <div className="absolute bottom-3 left-3">
        <p className="text-sm font-medium text-text-primary">{title}</p>
      </div>
    </Card>
  );
}




