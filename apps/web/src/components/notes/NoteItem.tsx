/**
 * Note Item Component
 * 
 * Individual note display item.
 * Uses placeholder data until API keys are added.
 */

import { FileText, Trash2 } from 'lucide-react';

interface NoteItemProps {
  id: string;
  title: string;
  content: string;
  sourceCount?: number;
  createdAt: string;
  isNew?: boolean;
  onDelete?: (id: string) => void;
}

export function NoteItem({ 
  id, 
  title, 
  content, 
  sourceCount = 0, 
  createdAt, 
  isNew = false,
  onDelete 
}: NoteItemProps) {
  const handleDelete = () => {
    if (onDelete) {
      onDelete(id);
    } else {
      // TODO: Replace with real API call when API keys are added
      alert('Note deletion will be available once API keys are configured');
    }
  };

  const formatTimeAgo = (date: string) => {
    const now = new Date();
    const noteDate = new Date(date);
    const diffMs = now.getTime() - noteDate.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return noteDate.toLocaleDateString();
  };

  return (
    <div className="group p-3 rounded-2xl bg-surface hover:bg-surface-hover transition-colors cursor-pointer">
      <div className="flex items-start gap-2">
        <FileText className="w-4 h-4 text-text-secondary mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-text-primary line-clamp-1">
            {title}
          </p>
          {content && (
            <p className="text-xs text-text-secondary mt-1 line-clamp-2">
              {content}
            </p>
          )}
          <div className="flex items-center gap-2 mt-2">
            {sourceCount > 0 && (
              <span className="text-xs text-text-tertiary">
                {sourceCount} source{sourceCount !== 1 ? 's' : ''}
              </span>
            )}
            <span className="text-xs text-text-tertiary">
              {formatTimeAgo(createdAt)}
            </span>
          </div>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleDelete();
          }}
          className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded-full hover:bg-surface-hover text-text-secondary hover:text-red-400"
          title="Delete note"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

