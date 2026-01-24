'use client';

import { createContext, useContext, useState, ReactNode, useCallback } from 'react';
import { Chat } from '@/hooks/useChats';

interface ChatContextType {
  currentChatId: string | null;
  currentChat: Chat | null;
  setCurrentChat: (chat: Chat | null) => void;
  setCurrentChatId: (chatId: string | null) => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export function ChatProvider({ children }: { children: ReactNode }) {
  const [currentChatId, setCurrentChatIdState] = useState<string | null>(null);
  const [currentChat, setCurrentChatState] = useState<Chat | null>(null);

  const setCurrentChat = useCallback((chat: Chat | null) => {
    setCurrentChatState(chat);
    setCurrentChatIdState(chat?.id || null);
  }, []);

  const setCurrentChatId = useCallback((chatId: string | null) => {
    setCurrentChatIdState(chatId);
    if (!chatId) {
      setCurrentChatState(null);
    }
  }, []);

  return (
    <ChatContext.Provider
      value={{
        currentChatId,
        currentChat,
        setCurrentChat,
        setCurrentChatId,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChatContext() {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChatContext must be used within a ChatProvider');
  }
  return context;
}
