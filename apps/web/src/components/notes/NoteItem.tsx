/**
 * Note Item Component
 * 
 * Individual note display item with edit and delete functionality.
 */

import { FileText, Trash2, Edit2, Link as LinkIcon } from 'lucide-react';

interface NoteItemProps {
  id: string;
  title: string;
  content: string;
  sourceRefId?: string;
  sourceCount?: number;
  createdAt: string;
  isNew?: boolean;
  onDelete?: (id: string) => void;
  onEdit?: (id: string) => void;
}

export function NoteItem({ 
  id, 
  title, 
  content, 
  sourceRefId,
  sourceCount = 0, 
  createdAt, 
  isNew = false,
  onDelete,
  onEdit
}: NoteItemProps) {
  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onDelete) {
      onDelete(id);
    }
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onEdit) {
      onEdit(id);
    }
  };

  const handleClick = () => {
    if (onEdit) {
      onEdit(id);
    }
  };

  const formatDate = (date: string) => {
    if (!date) {
      return 'Unknown date';
    }
    
    const noteDate = new Date(date);
    
    if (isNaN(noteDate.getTime())) {
      console.warn('[NoteItem] Invalid date received:', date);
      return 'Unknown date';
    }
    
    // Match the format used in SourceList: "Jan 15"
    return noteDate.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric'
    });
  };

  const formatFullDate = (date: string) => {
    const noteDate = new Date(date);
    if (isNaN(noteDate.getTime())) {
      return 'Unknown date';
    }
    return noteDate.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div 
      className="group p-3 rounded-2xl bg-surface hover:bg-surface-hover transition-colors cursor-pointer"
      onClick={handleClick}
    >
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
          <div className="flex items-center gap-3 mt-2 flex-wrap">
            {/* Creation Date */}
            <span 
              className="text-xs text-text-tertiary"
              title={formatFullDate(createdAt)}
            >
              {formatDate(createdAt)}
            </span>
            
            {/* Source Reference */}
            {sourceRefId && (
              <span 
                className="text-xs text-text-tertiary flex items-center gap-1"
                title={`Linked to source: ${sourceRefId}`}
              >
                <LinkIcon className="w-3 h-3" />
                Linked source
              </span>
            )}
            
            {/* Source Count (if multiple) */}
            {sourceCount > 1 && (
              <span className="text-xs text-text-tertiary">
                {sourceCount} sources
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {onEdit && (
            <button
              onClick={handleEdit}
              className="p-1 rounded-full hover:bg-surface-hover text-text-secondary hover:text-accent-blue transition-colors"
              title="Edit note"
            >
              <Edit2 className="w-4 h-4" />
            </button>
          )}
          {onDelete && (
            <button
              onClick={handleDelete}
              className="p-1 rounded-full hover:bg-surface-hover text-text-secondary hover:text-red-400 transition-colors"
              title="Delete note"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
