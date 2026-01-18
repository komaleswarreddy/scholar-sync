/**
 * Chat Interface Component
 * * Main chat area with messages and input.
 * Handles Section A: Chat Streaming requirements:
 * - Streaming error handling
 * - Network disconnection monitoring
 * - Retry mechanism
 * - Empty response handling
 */

'use client';

import { useState, useRef, useEffect } from 'react';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { ChatListSidebar } from './ChatListSidebar';
import { MessageCircle, RefreshCw, WifiOff, AlertTriangle, Menu, X } from 'lucide-react';
import { useApi } from '@/hooks/useApi';
import { useSourceContext } from '@/contexts/SourceContext';

interface Citation {
  id: string;
  sourceId: string;
  sourceTitle: string;
  text: string;
  source_id?: string;
  chunk_id?: string;
  page_number?: number;
  score?: number;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  citations?: Citation[];
  feedback?: 'thumbs_up' | 'thumbs_down' | null;
  messageId?: string; // Backend message ID for feedback
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [isOnline, setIsOnline] = useState(true);
  const [isLoadingChat, setIsLoadingChat] = useState(false);
  const [currentResponse, setCurrentResponse] = useState('');
  const [currentCitations, setCurrentCitations] = useState<Citation[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sidebarRefreshTrigger, setSidebarRefreshTrigger] = useState(0);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const lastUserMessageRef = useRef<string>(''); 
  const responseAccumulatorRef = useRef<string>(''); 
  const citationsAccumulatorRef = useRef<Citation[]>([]); 
  
  const { apiClient } = useApi();
  const { selectedSources } = useSourceContext();

  // Task A.e: Monitor network status
  useEffect(() => {
    const updateOnlineStatus = () => setIsOnline(navigator.onLine);
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    return () => {
      window.removeEventListener('online', updateOnlineStatus);
      window.removeEventListener('offline', updateOnlineStatus);
    };
  }, []);

  // Task C.c: Load previous chats on page load
  useEffect(() => {
    loadRecentChat();
  }, []);

  // Scroll to bottom when messages or current streaming response changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentResponse, isLoading]);

  // Task C.c: Load the most recent chat on mount
  const loadRecentChat = async () => {
    try {
      setIsLoadingChat(true);
      const chatList = await apiClient.listChats(1, 0);
      if (chatList.chats && chatList.chats.length > 0) {
        const recentChat = chatList.chats[0];
        await loadChat(recentChat.id);
      }
    } catch (error: any) {
      console.error('Failed to load recent chat:', error);
      // Show user-friendly error message
      if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
        setStreamError('Request timed out. Please check if the backend server is running.');
      } else if (error.code === 'ECONNREFUSED' || error.message?.includes('Failed to fetch')) {
        setStreamError('Cannot connect to server. Please check if the backend is running.');
      } else {
        // Continue without loading - user can start new chat
        setStreamError(null);
      }
    } finally {
      setIsLoadingChat(false);
    }
  };

  // Task C.c: Load a specific chat
  const loadChat = async (chatId: string) => {
    try {
      setIsLoadingChat(true);
      setStreamError(null); // Clear any previous errors
      setCurrentResponse(''); // Clear any streaming response
      const chat = await apiClient.getChat(chatId);
      if (chat) {
        setCurrentChatId(chat.id);
        if (chat.messages && Array.isArray(chat.messages) && chat.messages.length > 0) {
          const formattedMessages: Message[] = chat.messages.map((msg: any) => ({
            id: msg.id,
            role: msg.role as 'user' | 'assistant',
            content: msg.content,
            citations: msg.citations || [],
            messageId: msg.id,
            feedback: msg.feedback || null,
            timestamp: new Date(msg.created_at).toLocaleTimeString(),
          }));
          setMessages(formattedMessages);
        } else {
          setMessages([]);
        }
        setStreamError(null); // Clear error on success
      } else {
        setStreamError('Chat not found.');
        setCurrentChatId(null);
        setMessages([]);
      }
    } catch (error: any) {
      console.error('Failed to load chat:', error);
      let errorMessage = 'Failed to load chat history.';
      
      if (error.response?.status === 404) {
        errorMessage = 'Chat not found. It may have been deleted.';
        setCurrentChatId(null);
        setMessages([]);
      } else if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
        errorMessage = 'Request timed out. Please check if the backend server is running.';
      } else if (error.code === 'ECONNREFUSED' || error.message?.includes('Failed to fetch')) {
        errorMessage = 'Cannot connect to server. Please check if the backend is running.';
      } else if (error.response?.status === 500) {
        errorMessage = 'Server error. Please check backend logs.';
      }
      
      setStreamError(errorMessage);
      setCurrentChatId(null);
      setMessages([]);
    } finally {
      setIsLoadingChat(false);
    }
  };

  // Task C.d: Start a new chat
  const startNewChat = async () => {
    try {
      setIsLoadingChat(true);
      const newChat = await apiClient.createChat();
      setCurrentChatId(newChat.id);
      setMessages([]);
      setStreamError(null);
      // Refresh sidebar to show new chat
      setSidebarRefreshTrigger((prev) => prev + 1);
    } catch (error) {
      console.error('Failed to create new chat:', error);
      setStreamError('Failed to create new chat.');
    } finally {
      setIsLoadingChat(false);
    }
  };

  // Handle chat selection from sidebar
  const handleChatSelect = async (chatId: string) => {
    if (chatId === currentChatId) {
      // Already viewing this chat, no need to reload
      return;
    }
    try {
      await loadChat(chatId);
    } catch (error) {
      console.error('Failed to load selected chat:', error);
      // Error is already handled in loadChat, but ensure UI updates
    }
  };

  // Handle chat deletion callback
  const handleChatDeleted = () => {
    // Clear the current chat without creating a new one
    // The user can manually start a new chat if they want
    setCurrentChatId(null);
    setMessages([]);
    setStreamError(null);
  };

  const handleSend = async (message: string, activeSourceIds?: string[]) => {
    // Task A.e: Prevent sending if offline
    if (!navigator.onLine) {
      setStreamError("Network disconnected. Please check your internet connection.");
      return;
    }

    const sourceIds = activeSourceIds || Array.from(selectedSources);
    
    if (sourceIds.length === 0) {
      alert('Please select at least one source to chat with.');
      return;
    }
    
    if (!message.trim() || isLoading) return;

    // Task A.f: Store message for retry mechanism
    lastUserMessageRef.current = message;

    // Task C.b: Create chat if it doesn't exist
    let chatId = currentChatId;
    if (!chatId) {
      try {
        const newChat = await apiClient.createChat();
        chatId = newChat.id;
        setCurrentChatId(chatId);
      } catch (error) {
        console.error('Failed to create chat:', error);
        setStreamError('Failed to create chat session.');
        return;
      }
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      timestamp: new Date().toLocaleTimeString(),
    };
    
    setMessages((prev) => [...prev, userMessage]);

    if (chatId) {
      try {
        const savedMessage = await apiClient.addMessageToChat(chatId, 'user', message, []);
        if (savedMessage && savedMessage.id) {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === userMessage.id
                ? { ...msg, id: savedMessage.id, messageId: savedMessage.id, feedback: savedMessage.feedback || null }
                : msg
            )
          );
          setTimeout(() => {
            setSidebarRefreshTrigger((prev) => prev + 1);
          }, 500);
        }
      } catch (error: any) {
        console.error('Failed to save user message:', error);
      }
    }
    setIsLoading(true);
    setIsStreaming(false);
    setStreamError(null);
    setCurrentResponse('');
    setCurrentCitations([]);
    responseAccumulatorRef.current = '';
    citationsAccumulatorRef.current = [];

    try {
      const history = messages
        .map((m) => ({
          role: m.role,
          content: m.content,
        }));

      await apiClient.streamChat(
        message,
        history,
        sourceIds,
        // onChunk
        (text: string) => {
          setIsStreaming(true);
          setStreamError(null);
          responseAccumulatorRef.current += text;
          setCurrentResponse(responseAccumulatorRef.current);
        },
        // onCitation
        (citation: Citation) => {
          citationsAccumulatorRef.current = [...citationsAccumulatorRef.current, citation];
          setCurrentCitations(citationsAccumulatorRef.current);
        },
        // onDone
        async () => {
          setIsStreaming(false);
          const finalResponse = responseAccumulatorRef.current;
          const finalCitations = citationsAccumulatorRef.current;
          
          // Task A.d: Handle empty responses
          if (finalResponse && finalResponse.trim()) {
            const assistantMessage: Message = {
              id: (Date.now() + 1).toString(),
              role: 'assistant',
              content: finalResponse,
              citations: finalCitations,
              timestamp: new Date().toLocaleTimeString(),
            };
            setMessages((prev) => [...prev, assistantMessage]);

            if (currentChatId) {
              try {
                const savedMessage = await apiClient.addMessageToChat(
                  currentChatId,
                  'assistant',
                  finalResponse,
                  finalCitations
                );
                if (savedMessage && savedMessage.id) {
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantMessage.id
                        ? { ...msg, id: savedMessage.id, messageId: savedMessage.id, feedback: savedMessage.feedback || null }
                        : msg
                    )
                  );
                } else {
                  // If save failed, still show buttons but they'll be disabled
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === assistantMessage.id
                        ? { ...msg, messageId: undefined }
                        : msg
                    )
                  );
                }
                setSidebarRefreshTrigger((prev) => prev + 1);
              } catch (error: any) {
                console.error('Failed to save assistant message:', error);
              }
            }
          } else {
            setStreamError("Received an empty response from the assistant.");
          }
          
          resetStreamingState();
        },
        // onError - Task A.b: Handle streaming errors gracefully
        (error: string) => {
          console.error('Streaming error:', error);
          setStreamError(error);
          setIsStreaming(false);
          setIsLoading(false);
          
          // Save partial work if it exists
          if (responseAccumulatorRef.current.trim()) {
            const partialMessage: Message = {
              id: (Date.now() + 1).toString(),
              role: 'assistant',
              content: responseAccumulatorRef.current + "\n\n[Stream Interrupted]",
              citations: citationsAccumulatorRef.current,
              timestamp: new Date().toLocaleTimeString(),
            };
            setMessages((prev) => [...prev, partialMessage]);
          }
        }
      );
    } catch (error: any) {
      // Task A.b & A.e
      setStreamError(error.message || 'Failed to connect to the chat service.');
      setIsLoading(false);
      setIsStreaming(false);
    }
  };

  const resetStreamingState = () => {
    setCurrentResponse('');
    setCurrentCitations([]);
    responseAccumulatorRef.current = '';
    citationsAccumulatorRef.current = [];
    setIsLoading(false);
  };

  // Task A.f: Retry functionality
  const handleRetry = () => {
    if (lastUserMessageRef.current) {
      setStreamError(null);
      handleSend(lastUserMessageRef.current);
    }
  };

  return (
    <div className="flex h-full bg-surface">
      {/* Chat List Sidebar */}
      <div className={`${sidebarOpen ? 'w-64' : 'w-0'} transition-all duration-300 overflow-hidden border-r border-border-default`}>
        <ChatListSidebar
          currentChatId={currentChatId}
          onChatSelect={handleChatSelect}
          onNewChat={startNewChat}
          onChatDeleted={handleChatDeleted}
          className="h-full"
          refreshTrigger={sidebarRefreshTrigger}
        />
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Task A.e: Network status indicator */}
        {!isOnline && (
          <div className="bg-red-600 text-white text-[11px] py-1.5 px-4 flex items-center justify-center gap-2">
            <WifiOff className="w-3 h-3" />
            Offline Mode: Check your connection to continue chatting
          </div>
        )}

        <div className="border-b border-border-default p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="p-1.5 rounded-lg hover:bg-surface-hover transition-colors text-text-secondary hover:text-text-primary"
                title={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
              >
                {sidebarOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
              </button>
              <div className="flex items-center gap-2">
                <MessageCircle className="w-5 h-5 text-text-secondary" />
                <h1 className="text-lg font-medium text-text-primary">Chat</h1>
              </div>
            </div>
            {/* Task C.d: New Chat Button */}
            <button
              onClick={startNewChat}
              disabled={isLoadingChat}
              className="px-3 py-1.5 text-xs font-semibold bg-surface-subtle border border-border-default rounded-lg text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoadingChat ? 'Loading...' : '+ New Chat'}
            </button>
          </div>
        </div>

      <div className="flex-1 overflow-y-auto px-4 py-6">
        {isLoadingChat ? (
          <div className="flex flex-col items-center justify-center h-full p-8">
            <div className="flex gap-1 mb-2">
              <div className="w-1.5 h-1.5 bg-text-tertiary rounded-full animate-bounce [animation-delay:-0.3s]" />
              <div className="w-1.5 h-1.5 bg-text-tertiary rounded-full animate-bounce [animation-delay:-0.15s]" />
              <div className="w-1.5 h-1.5 bg-text-tertiary rounded-full animate-bounce" />
            </div>
            <p className="text-text-tertiary text-sm">Loading chat...</p>
          </div>
        ) : messages.length === 0 && !currentChatId ? (
          <div className="flex flex-col items-center justify-center h-full p-8">
            <p className="text-text-secondary text-center mb-2">
              Start a conversation by selecting sources and asking a question.
            </p>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                role={message.role}
                content={message.content}
                citations={message.citations}
                timestamp={message.timestamp}
                messageId={message.messageId || message.id}
                feedback={message.feedback}
                onFeedbackUpdate={(messageId, feedback) => {
                  // Update local state when feedback changes
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === messageId ? { ...msg, feedback } : msg
                    )
                  );
                }}
              />
            ))}
            
            {/* Task A.c: Combined loading and streaming states */}
            {isLoading && (
              <div className="space-y-4">
                {(currentResponse || isStreaming) ? (
                  <ChatMessage
                    role="assistant"
                    content={currentResponse}
                    citations={currentCitations}
                  />
                ) : (
                  <div className="flex items-center gap-3 p-4 bg-surface-subtle rounded-2xl w-fit">
                    <div className="flex gap-1">
                      <div className="w-1.5 h-1.5 bg-text-tertiary rounded-full animate-bounce [animation-delay:-0.3s]" />
                      <div className="w-1.5 h-1.5 bg-text-tertiary rounded-full animate-bounce [animation-delay:-0.15s]" />
                      <div className="w-1.5 h-1.5 bg-text-tertiary rounded-full animate-bounce" />
                    </div>
                    <span className="text-xs font-medium text-text-tertiary uppercase tracking-wider">Thinking</span>
                  </div>
                )}
              </div>
            )}

            {/* Task A.b & A.f: Visible Error State with Retry Button */}
            {streamError && (
              <div className="p-4 rounded-2xl bg-red-50 border border-red-100 space-y-3">
                <div className="flex items-start gap-2 text-red-700">
                  <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <div className="text-sm font-medium leading-relaxed">{streamError}</div>
                </div>
                <button 
                  onClick={handleRetry}
                  className="flex items-center gap-2 px-3 py-1.5 bg-white border border-red-200 text-red-700 text-xs font-bold rounded-lg hover:bg-red-50 transition-colors"
                >
                  <RefreshCw className="w-3 h-3" />
                  Retry Request
                </button>
              </div>
            )}
            <div ref={messagesEndRef} className="h-4" />
          </div>
        )}
      </div>

        <div className="p-4 bg-surface border-t border-border-default">
          <ChatInput 
            onSend={handleSend} 
            disabled={isLoading || !isOnline} 
            activeSourceIds={Array.from(selectedSources)}
          />
        </div>
      </div>
    </div>
  );
}