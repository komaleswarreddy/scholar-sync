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
}

export function StudioCard({ icon, title, onClick }: StudioCardProps) {
  const handleClick = () => {
    if (onClick) {
      onClick();
    } else {
      // TODO: Replace with real API call when API keys are added
      alert(`${title} generation will be available once API keys are configured`);
    }
  };

  return (
    <Card hover onClick={handleClick} className="h-[88px] relative">
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



