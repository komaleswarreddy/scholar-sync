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
import { handleApiError, getUserFriendlyMessage } from '@/lib/error-handler';

interface Citation {
  id?: string;
  sourceId?: string;
  sourceTitle?: string;
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
  question?: string; // The question that was asked (for assistant messages)
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
  const [currentQuestion, setCurrentQuestion] = useState<string>('');
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
      // Use standardized error handling
      const apiError = error.apiError || handleApiError(error);
      const errorMessage = getUserFriendlyMessage(apiError);
      setStreamError(errorMessage);
      // Continue without loading - user can start new chat
    } finally {
      setIsLoadingChat(false);
    }
  };

  // Task C.c: Load a specific chat
  const loadChat = async (chatId: string) => {
    try {
      setIsLoadingChat(true);
      // Clear all streaming state before loading chat (but don't clear messages yet)
      setCurrentResponse('');
      setCurrentCitations([]);
      responseAccumulatorRef.current = '';
      citationsAccumulatorRef.current = [];
      setIsLoading(false);
      setIsStreaming(false);
      setStreamError(null); // Clear any previous errors
      
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
      // Use standardized error handling
      const apiError = error.apiError || handleApiError(error);
      const errorMessage = getUserFriendlyMessage(apiError);
      
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
      // Clear all streaming state before creating new chat
      resetStreamingState();
      setStreamError(null);
      const newChat = await apiClient.createChat();
      setCurrentChatId(newChat.id);
      setMessages([]);
      // Refresh sidebar to show new chat
      setSidebarRefreshTrigger((prev) => prev + 1);
    } catch (error: any) {
      console.error('Failed to create new chat:', error);
      // Use standardized error handling
      const apiError = error.apiError || handleApiError(error);
      const errorMessage = getUserFriendlyMessage(apiError);
      setStreamError(errorMessage);
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
    resetStreamingState();
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
      setStreamError('Please select at least one source to chat with.');
      return;
    }
    
    if (!message.trim() || isLoading) return;

    // Task A.f: Store message for retry mechanism
    lastUserMessageRef.current = message;

    // Task C.b: Create chat if it doesn't exist
    let chatId = currentChatId;
    if (!chatId) {
      try {
        setIsLoading(true);
        const newChat = await apiClient.createChat();
        chatId = newChat.id;
        setCurrentChatId(chatId);
      } catch (error: any) {
        console.error('Failed to create chat:', error);
        // Use standardized error handling
        const apiError = error.apiError || handleApiError(error);
        const errorMessage = getUserFriendlyMessage(apiError);
        setStreamError(errorMessage);
        setIsLoading(false);
        return;
      }
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      timestamp: new Date().toLocaleTimeString(),
      question: message.trim(),
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
        // Non-blocking error - message is already displayed, just log it
        // Use standardized error handling for logging
        const apiError = error.apiError || handleApiError(error);
        // Non-blocking error - message is already displayed
      }
    }
    // Reset all streaming state before sending
    resetStreamingState();
    setIsLoading(true);
    setStreamError(null);

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
          // Ensure source_title is mapped to sourceTitle for frontend compatibility
          const mappedCitation: Citation = {
            ...citation,
            sourceTitle: citation.sourceTitle || (citation as any).source_title,
          };
          citationsAccumulatorRef.current = [...citationsAccumulatorRef.current, mappedCitation];
          setCurrentCitations(citationsAccumulatorRef.current);
        },
        // onDone
        async () => {
          setIsStreaming(false);
          const finalResponse = responseAccumulatorRef.current;
          const allCitations = citationsAccumulatorRef.current;
          
          // Filter citations to only include those referenced in the response text
          // Track citations in order of appearance (not just unique numbers)
          const referencedCitationNumbers: number[] = [];
          const seenNumbers = new Set<number>();
          
          // Parse citation patterns: [1], [1, 4], [4, 6, 9], etc.
          // Match patterns like [1], [1, 4], [4, 6, 9] where numbers can be comma-separated
          const citationPattern = /\[(\d+(?:\s*,\s*\d+)*)\]/g;
          let match;
          
          // Reset regex lastIndex
          citationPattern.lastIndex = 0;
          
          while ((match = citationPattern.exec(finalResponse)) !== null) {
            // Extract all numbers from the match (e.g., "1, 4" or "4, 6, 9")
            const numbersStr = match[1];
            const numbers = numbersStr.split(',').map(num => parseInt(num.trim(), 10));
            
            numbers.forEach(citationNum => {
              if (citationNum > 0 && citationNum <= allCitations.length) {
                // Track order of appearance, but only add each number once
                if (!seenNumbers.has(citationNum)) {
                  referencedCitationNumbers.push(citationNum);
                  seenNumbers.add(citationNum);
                }
              }
            });
          }
          
          let filteredCitations: Citation[] = [];
          let finalResponseText = finalResponse;
          
          // If we found referenced citations, filter them
          if (referencedCitationNumbers.length > 0 && allCitations.length > 0) {
            // Create a map of original citation number to citation object
            const citationMap = new Map<number, Citation>();
            allCitations.forEach((citation, index) => {
              citationMap.set(index + 1, citation); // Map 1-based index to citation
            });
            
            // Get citations in order of appearance in text (preserve order)
            referencedCitationNumbers.forEach((originalNum) => {
              const citation = citationMap.get(originalNum);
              if (citation) {
                filteredCitations.push(citation);
              }
            });
            
            // Check if response has comma-separated citations (e.g., [1, 4], [4, 6, 9])
            // If so, don't renumber - keep original numbers to preserve meaning
            const hasCommaSeparatedCitations = /\[\d+\s*,\s*\d+/.test(finalResponse);
            
            if (!hasCommaSeparatedCitations) {
              // Only renumber if we have single citations (e.g., [1], [2])
              // Process in reverse order to avoid renumbering conflicts
              for (let i = referencedCitationNumbers.length - 1; i >= 0; i--) {
                const originalNum = referencedCitationNumbers[i];
                const newNum = i + 1;
                if (originalNum !== newNum) {
                  // Replace [originalNum] with [newNum] in the response (only single citations)
                  finalResponseText = finalResponseText.replace(
                    new RegExp(`\\[${originalNum}\\]`, 'g'),
                    `[${newNum}]`
                  );
                }
              }
            }
            // If comma-separated citations exist, keep original numbers
          } else {
            // Fallback: if no citations are referenced in text, show all citations
            // This handles cases where Gemini doesn't include citation markers or markers aren't found
            filteredCitations = allCitations;
            finalResponseText = finalResponse;
          }
          
          // Task A.d: Handle empty responses
          if (finalResponseText && finalResponseText.trim()) {
            const assistantMessage: Message = {
              id: (Date.now() + 1).toString(),
              role: 'assistant',
              content: finalResponseText, // Use final response (may be renumbered or original)
              citations: filteredCitations,
              timestamp: new Date().toLocaleTimeString(),
              question: currentQuestion,
            };
            setMessages((prev) => [...prev, assistantMessage]);

            if (currentChatId) {
              try {
                // Format citations for backend (ensure they have required fields)
                // Use filteredCitations instead of finalCitations
                const formattedCitations = filteredCitations.map((citation) => ({
                  source_id: citation.sourceId || citation.source_id || '',
                  chunk_id: citation.chunk_id || '',
                  text: citation.text || '',
                  page_number: citation.page_number || null,
                  score: citation.score || 0,
                }));
                
                const savedMessage = await apiClient.addMessageToChat(
                  currentChatId,
                  'assistant',
                  finalResponseText, // Use final response
                  formattedCitations
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
                  console.error('Failed to save assistant message: No message ID returned');
                }
                setSidebarRefreshTrigger((prev) => prev + 1);
              } catch (error: any) {
                console.error('Failed to save assistant message:', error);
                // Show error to user but keep the message visible
                setStreamError(`Response received but failed to save: ${error?.message || 'Unknown error'}`);
              }
            } else {
              console.error('Cannot save assistant message: No chat ID');
            }
          } else {
            // Check if we have citations but no text - this might indicate a backend issue
            if (finalCitations.length > 0) {
              setStreamError("Received citations but no text response. The model may have been blocked or encountered an error. Please try again.");
            } else {
              setStreamError("Received an empty response from the assistant. Please try again or rephrase your question.");
            }
          }
          
          // Always reset streaming state after done, regardless of whether response was empty
          resetStreamingState();
        },
        // onError - Task A.b: Handle streaming errors gracefully
        (error: string) => {
          console.error('Streaming error:', error);
          setStreamError(error);
          setIsStreaming(false);
          
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
          
          // Always reset streaming state on error
          resetStreamingState();
        }
      );
    } catch (error: any) {
      // Task A.b & A.e
      // Ensure we always set a string, not an Error object
      const errorMessage = error?.message || error?.apiError?.message || error?.toString() || 'Failed to connect to the chat service.';
      setStreamError(errorMessage);
      // Always reset streaming state on error
      resetStreamingState();
    }
  };

  const resetStreamingState = () => {
    setCurrentResponse('');
    setCurrentCitations([]);
    responseAccumulatorRef.current = '';
    citationsAccumulatorRef.current = [];
    setIsLoading(false);
    setIsStreaming(false);
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
                question={message.question}
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
                {(currentResponse || isStreaming || currentCitations.length > 0) ? (
                  <ChatMessage
                    role="assistant"
                    content={currentResponse || (currentCitations.length > 0 ? 'Generating response...' : '')}
                    citations={currentCitations}
                    question={currentQuestion}
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