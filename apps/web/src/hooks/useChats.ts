/**
 * TanStack Query hooks for Chats API
 * 
 * Provides loading states, caching, and optimistic updates for chat operations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { handleApiError, getUserFriendlyMessage } from '@/lib/error-handler';

// Query keys
export const chatKeys = {
  all: ['chats'] as const,
  lists: () => [...chatKeys.all, 'list'] as const,
  list: (limit?: number, offset?: number) =>
    [...chatKeys.lists(), { limit, offset }] as const,
  details: () => [...chatKeys.all, 'detail'] as const,
  detail: (id: string) => [...chatKeys.details(), id] as const,
};

// Types
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: any[];
  created_at: string;
  feedback?: 'thumbs_up' | 'thumbs_down' | null;
}

export interface Chat {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  messages?: ChatMessage[];
}

export interface ChatListResponse {
  chats: Chat[];
  total: number;
}

/**
 * Hook to fetch chat list
 */
export function useChats(limit: number = 50, offset: number = 0) {
  return useQuery({
    queryKey: chatKeys.list(limit, offset),
    queryFn: async () => {
      try {
        const result = await apiClient.listChats(limit, offset);
        return result as ChatListResponse;
      } catch (error: any) {
        const apiError = error.apiError || handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    staleTime: 30 * 1000, // 30 seconds
  });
}

/**
 * Hook to fetch a single chat with messages
 */
export function useChat(chatId: string | null) {
  return useQuery({
    queryKey: chatKeys.detail(chatId || ''),
    queryFn: async () => {
      if (!chatId) return null;
      try {
        const result = await apiClient.getChat(chatId);
        return result as Chat;
      } catch (error: any) {
        const apiError = error.apiError || handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    enabled: !!chatId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to create a chat
 */
export function useCreateChat() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (title?: string) => {
      try {
        const result = await apiClient.createChat(title);
        return result as Chat;
      } catch (error: any) {
        const apiError = error.apiError || handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    onSuccess: (newChat) => {
      // Invalidate chat list to refetch
      queryClient.invalidateQueries({ queryKey: chatKeys.lists() });
      // Set the new chat in cache
      if (newChat?.id) {
        queryClient.setQueryData(chatKeys.detail(newChat.id), newChat);
      }
    },
  });
}

/**
 * Hook to update chat title
 */
export function useUpdateChatTitle() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ chatId, title }: { chatId: string; title: string }) => {
      try {
        const result = await apiClient.updateChatTitle(chatId, title);
        return result as Chat;
      } catch (error: any) {
        const apiError = error.apiError || handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    // Optimistic update: update chat title in cache immediately
    onMutate: async ({ chatId, title }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: chatKeys.detail(chatId) });
      await queryClient.cancelQueries({ queryKey: chatKeys.lists() });

      // Snapshot the previous values
      const previousChat = queryClient.getQueryData<Chat>(chatKeys.detail(chatId));
      const previousChatList = queryClient.getQueryData<ChatListResponse>(
        chatKeys.list()
      );

      // Optimistically update the chat
      if (previousChat) {
        queryClient.setQueryData<Chat>(chatKeys.detail(chatId), {
          ...previousChat,
          title,
          updated_at: new Date().toISOString(),
        });
      }

      // Optimistically update the chat in the list
      queryClient.setQueryData<ChatListResponse>(chatKeys.list(), (old) => {
        if (!old) return old;
        return {
          ...old,
          chats: old.chats.map((chat) =>
            chat.id === chatId
              ? { ...chat, title, updated_at: new Date().toISOString() }
              : chat
          ),
        };
      });

      // Return context with snapshotted values
      return { previousChat, previousChatList };
    },
    // If the mutation fails, use the context to roll back
    onError: (err, variables, context) => {
      if (context?.previousChat) {
        queryClient.setQueryData(chatKeys.detail(variables.chatId), context.previousChat);
      }
      if (context?.previousChatList) {
        queryClient.setQueryData(chatKeys.list(), context.previousChatList);
      }
    },
    // Always refetch after error or success
    onSettled: (data, error, variables) => {
      queryClient.invalidateQueries({ queryKey: chatKeys.detail(variables.chatId) });
      queryClient.invalidateQueries({ queryKey: chatKeys.lists() });
    },
  });
}

/**
 * Hook to delete a chat
 */
export function useDeleteChat() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (chatId: string) => {
      try {
        await apiClient.deleteChat(chatId);
        return chatId;
      } catch (error: any) {
        const apiError = error.apiError || handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    // Optimistic update: remove chat from cache immediately
    onMutate: async (chatId) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: chatKeys.detail(chatId) });
      await queryClient.cancelQueries({ queryKey: chatKeys.lists() });

      // Snapshot the previous values
      const previousChat = queryClient.getQueryData<Chat>(chatKeys.detail(chatId));
      const previousChatList = queryClient.getQueryData<ChatListResponse>(
        chatKeys.list()
      );

      // Optimistically remove the chat from the list
      queryClient.setQueryData<ChatListResponse>(chatKeys.list(), (old) => {
        if (!old) return old;
        return {
          ...old,
          chats: old.chats.filter((chat) => chat.id !== chatId),
          total: Math.max(0, old.total - 1),
        };
      });

      // Remove the chat from cache
      queryClient.removeQueries({ queryKey: chatKeys.detail(chatId) });

      // Return context with snapshotted values
      return { previousChat, previousChatList };
    },
    // If the mutation fails, use the context to roll back
    onError: (err, chatId, context) => {
      if (context?.previousChat) {
        queryClient.setQueryData(chatKeys.detail(chatId), context.previousChat);
      }
      if (context?.previousChatList) {
        queryClient.setQueryData(chatKeys.list(), context.previousChatList);
      }
    },
    // Always refetch after error or success
    onSettled: (data, error, chatId) => {
      queryClient.invalidateQueries({ queryKey: chatKeys.lists() });
      queryClient.removeQueries({ queryKey: chatKeys.detail(chatId) });
    },
  });
}

/**
 * Hook to add a message to a chat
 */
export function useAddMessageToChat() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      chatId,
      role,
      content,
      citations,
    }: {
      chatId: string;
      role: 'user' | 'assistant';
      content: string;
      citations?: any[];
    }) => {
      try {
        const result = await apiClient.addMessageToChat(chatId, role, content, citations);
        return result;
      } catch (error: any) {
        const apiError = error.apiError || handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    onSuccess: (data, variables) => {
      // Invalidate the chat to refetch with new message
      queryClient.invalidateQueries({ queryKey: chatKeys.detail(variables.chatId) });
    },
  });
}

/**
 * Hook to update message feedback
 */
export function useUpdateMessageFeedback() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      messageId,
      feedback,
    }: {
      messageId: string;
      feedback: 'thumbs_up' | 'thumbs_down' | null;
    }) => {
      try {
        const result = await apiClient.updateMessageFeedback(messageId, feedback);
        return result;
      } catch (error: any) {
        const apiError = error.apiError || handleApiError(error);
        throw new Error(getUserFriendlyMessage(apiError));
      }
    },
    // Optimistic update: update feedback in cache immediately
    onMutate: async ({ messageId, feedback }) => {
      // Find all chat queries that might contain this message
      const queryCache = queryClient.getQueryCache();
      const chatQueries = queryCache.findAll({ queryKey: chatKeys.details() });

      // Cancel any outgoing refetches
      await Promise.all(
        chatQueries.map((query) =>
          queryClient.cancelQueries({ queryKey: query.queryKey })
        )
      );

      // Snapshot previous values
      const previousChats = chatQueries.map((query) => ({
        queryKey: query.queryKey,
        data: query.state.data,
      }));

      // Optimistically update feedback in all chats
      chatQueries.forEach((query) => {
        const chat = query.state.data as Chat | undefined;
        if (chat?.messages) {
          const updatedChat: Chat = {
            ...chat,
            messages: chat.messages.map((msg) =>
              msg.id === messageId ? { ...msg, feedback } : msg
            ),
          };
          queryClient.setQueryData(query.queryKey, updatedChat);
        }
      });

      return { previousChats };
    },
    // If the mutation fails, roll back
    onError: (err, variables, context) => {
      if (context?.previousChats) {
        context.previousChats.forEach(({ queryKey, data }) => {
          queryClient.setQueryData(queryKey, data);
        });
      }
    },
    // Always refetch after error or success
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: chatKeys.details() });
    },
  });
}
