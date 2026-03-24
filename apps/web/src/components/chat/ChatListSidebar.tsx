/**
 * Chat List Sidebar Component
 * 
 * Task C.e: Optional sidebar to show list of chats.
 * Displays chat history with ability to switch between chats.
 */

'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { MessageCircle, Plus, Trash2, Loader2, AlertCircle } from 'lucide-react';
import { useApi } from '@/hooks/useApi';
import { handleApiError, getUserFriendlyMessage, ErrorType } from '@/lib/error-handler';

interface ChatListItem {
  id: string;
  title: string | null;
  created_at: string;
  message_count: number;
}

interface ChatListSidebarProps {
  currentChatId: string | null;
  onChatSelect: (chatId: string) => void;
  onNewChat: () => void;
  className?: string;
  onChatDeleted?: () => void;
  refreshTrigger?: number; // Trigger refresh when this changes
}

export function ChatListSidebar({
  currentChatId,
  onChatSelect,
  onNewChat,
  className = '',
  onChatDeleted,
  refreshTrigger,
}: ChatListSidebarProps) {
  const [chats, setChats] = useState<ChatListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const retryCountRef = useRef(0);
  const { apiClient } = useApi();

  // Load chat list with automatic retry for network errors
  const loadChats = useCallback(async (isRetry: boolean = false) => {
    try {
      setIsLoading(true);
      if (!isRetry) {
        setError(null);
        retryCountRef.current = 0;
      }
      
      const response = await apiClient.listChats(50, 0);
      
      // Handle different response formats
      if (response) {
        if (Array.isArray(response)) {
          setChats(response);
        } else if (response.chats && Array.isArray(response.chats)) {
          setChats(response.chats);
        }
        // Clear any previous errors on successful load
        setError(null);
        retryCountRef.current = 0;
      } else {
        setChats((prev) => prev.length > 0 ? prev : []);
      }
    } catch (error: any) {
      // Error is handled by TanStack Query error state
      // Use standardized error handling
      const apiError = error.apiError || handleApiError(error);
      const errorMessage = getUserFriendlyMessage(apiError);
      
      const isRetryableList =
        apiError.retryable &&
        (apiError.type === ErrorType.NETWORK || apiError.type === ErrorType.TIMEOUT);

      // Auto-retry slow/offline responses up to 2 times
      if (isRetryableList && retryCountRef.current < 2) {
        retryCountRef.current += 1;

        if (chats.length === 0) {
          setError(errorMessage);
        }

        setTimeout(() => {
          loadChats(true);
        }, 1000 * retryCountRef.current);

        setChats((prev) => (prev.length > 0 ? prev : []));
      } else {
        retryCountRef.current = 0;
        setChats((prev) => {
          if (prev.length === 0) {
            setError(errorMessage);
          } else {
            setError(null);
            console.warn('Chat list refresh failed (keeping cached list):', errorMessage);
          }
          return prev.length > 0 ? prev : [];
        });
      }
    } finally {
      setIsLoading(false);
    }
  }, [apiClient, chats.length]);

  useEffect(() => {
    loadChats();
  }, [loadChats]);

  // Refresh when trigger changes (e.g., new chat created)
  useEffect(() => {
    if (refreshTrigger !== undefined && refreshTrigger > 0) {
      loadChats();
    }
  }, [refreshTrigger, loadChats]);

  const handleDeleteChat = async (chatId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    
    const confirmed = window.confirm(
      'Are you sure you want to delete this chat? This action cannot be undone.'
    );
    if (!confirmed) return;

    setDeletingId(chatId);
    try {
      await apiClient.deleteChat(chatId);
      setChats((prev) => prev.filter((chat) => chat.id !== chatId));
      
      if (currentChatId === chatId && onChatDeleted) {
        onChatDeleted();
      }
      
      await loadChats();
    } catch (error: any) {
      console.error('Failed to delete chat:', error);
      // Use standardized error handling
      const apiError = error.apiError || handleApiError(error);
      const errorMessage = getUserFriendlyMessage(apiError);
      setError(errorMessage);
      await loadChats();
    } finally {
      setDeletingId(null);
    }
  };

  const formatChatTitle = (title: string | null, createdAt: string): string => {
    if (title) return title;
    const date = new Date(createdAt);
    return `Chat ${date.toLocaleDateString()}`;
  };

  return (
    <div className={`flex flex-col h-full bg-surface border-r border-border-default ${className}`}>
      {/* Header */}
      <div className="h-14 flex items-center px-4 border-b border-border-default">
        <div className="flex items-center justify-between w-full">
          <h2 className="text-lg font-bold text-text-primary">Chats</h2>
          <button
            onClick={onNewChat}
            className="p-1.5 rounded-lg hover:bg-surface-hover transition-colors text-text-secondary hover:text-text-primary"
            title="New Chat"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-3 mx-4 mt-2 rounded-lg bg-red-50 border border-red-200 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-xs text-red-700 font-medium">{error}</p>
            <button
              onClick={() => {
                setError(null);
                retryCountRef.current = 0;
                loadChats();
              }}
              className="text-xs text-red-600 hover:text-red-800 mt-1 underline"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Chat List */}
      <div className="flex-1 overflow-y-auto p-2">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-text-tertiary mb-2" />
            <p className="text-text-tertiary text-xs">Loading chats...</p>
          </div>
        ) : chats.length === 0 ? (
          <div className="text-center py-12 px-4">
            <MessageCircle className="w-8 h-8 text-text-tertiary mx-auto mb-2" />
            <p className="text-text-secondary text-sm font-semibold mb-1">No chats yet</p>
            <p className="text-text-tertiary text-xs">Start a new conversation</p>
            {process.env.NODE_ENV === 'development' && (
              <p className="text-text-tertiary text-xs mt-2">
                (Check console for loading errors)
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-1">
            {chats.map((chat) => {
              const isActive = currentChatId === chat.id;
              const isDeleting = deletingId === chat.id;

              return (
                <div
                  key={chat.id}
                  onClick={() => !isDeleting && onChatSelect(chat.id)}
                  className={`
                    flex items-center justify-between gap-2 p-3 rounded-xl cursor-pointer transition-all group
                    ${isActive 
                      ? 'bg-surface-hover border border-border-default' 
                      : 'hover:bg-surface-subtle border border-transparent'
                    }
                    ${isDeleting ? 'opacity-50' : ''}
                  `}
                >
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-semibold truncate ${isActive ? 'text-text-primary' : 'text-text-secondary'}`}>
                      {formatChatTitle(chat.title, chat.created_at)}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <p className="text-xs font-medium text-text-tertiary">
                        {chat.message_count} {chat.message_count === 1 ? 'message' : 'messages'}
                      </p>
                      <span className="text-text-tertiary text-xs">•</span>
                      <p className="text-xs text-text-tertiary">
                        {new Date(chat.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  
                  <button
                    onClick={(e) => handleDeleteChat(chat.id, e)}
                    disabled={isDeleting}
                    className={`p-1.5 rounded-lg transition-all opacity-0 group-hover:opacity-100 text-text-tertiary hover:text-red-600 hover:bg-red-50 ${
                      isDeleting ? 'opacity-100' : ''
                    }`}
                    title="Delete chat"
                  >
                    {isDeleting ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-red-600" />
                    ) : (
                      <Trash2 className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
