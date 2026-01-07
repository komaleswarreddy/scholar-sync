/**
 * Chat Interface Component
 * 
 * Main chat area with messages and input.
 * Uses placeholder messages until API keys are added.
 */

'use client';

import { useState, useRef, useEffect } from 'react';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { MessageCircle } from 'lucide-react';
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
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentResponse, setCurrentResponse] = useState('');
  const [currentCitations, setCurrentCitations] = useState<Citation[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { apiClient } = useApi();
  const { selectedSources } = useSourceContext();

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentResponse]);

  const handleSend = async (message: string, activeSourceIds?: string[]) => {
    // Use selected sources if not provided
    const sourceIds = activeSourceIds || Array.from(selectedSources);
    
    // Validate that at least one source is selected
    if (sourceIds.length === 0) {
      alert('Please select at least one source to chat with.');
      return;
    }
    
    if (!message.trim() || isLoading) return;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      timestamp: new Date().toLocaleTimeString(),
    };
    
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setCurrentResponse('');
    setCurrentCitations([]);

    try {
      // Convert messages to API format
      const history = messages
        .filter((m) => m.role !== 'user' || m.content !== message)
        .map((m) => ({
          role: m.role,
          content: m.content,
        }));

      // Stream chat response
      await apiClient.streamChat(
        message,
        history,
        sourceIds,
        // onChunk
        (text: string) => {
          setCurrentResponse((prev) => prev + text);
        },
        // onCitation
        (citation: Citation) => {
          setCurrentCitations((prev) => [...prev, citation]);
        },
        // onDone
        () => {
          // Save the complete response as a message
          if (currentResponse) {
            const assistantMessage: Message = {
              id: (Date.now() + 1).toString(),
              role: 'assistant',
              content: currentResponse,
              citations: currentCitations,
              timestamp: new Date().toLocaleTimeString(),
            };
            setMessages((prev) => [...prev, assistantMessage]);
          }
          setCurrentResponse('');
          setCurrentCitations([]);
          setIsLoading(false);
        }
      );
    } catch (error: any) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: error.response?.data?.detail || 'Failed to get response. Please check your API keys configuration.',
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      setIsLoading(false);
      setCurrentResponse('');
      setCurrentCitations([]);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Chat Header */}
      <div className="border-b border-border-default p-4">
        <div className="flex items-center gap-2">
          <MessageCircle className="w-5 h-5 text-text-secondary" />
          <h1 className="text-lg font-medium text-text-primary">Chat</h1>
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full p-8">
            <p className="text-text-secondary text-center mb-2">
              Start a conversation by selecting sources and asking a question.
            </p>
            <p className="text-text-tertiary text-sm text-center">
              Configure API keys to enable full chat functionality
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                role={message.role}
                content={message.content}
                citations={message.citations}
                timestamp={message.timestamp}
              />
            ))}
            {isLoading && currentResponse && (
              <ChatMessage
                role="assistant"
                content={currentResponse}
                citations={currentCitations}
              />
            )}
            {isLoading && !currentResponse && (
              <div className="p-4">
                <div className="flex items-center gap-2 text-text-secondary">
                  <div className="w-2 h-2 bg-accent-blue rounded-full animate-pulse" />
                  <span className="text-sm">Thinking...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Chat Input */}
      <ChatInput 
        onSend={handleSend} 
        disabled={isLoading} 
        activeSourceIds={Array.from(selectedSources)}
      />
    </div>
  );
}

