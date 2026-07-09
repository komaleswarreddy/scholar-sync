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

import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { ChatMessage, displayAssistantText } from './ChatMessage';
import { ChatStudioSelectionToolbar } from './ChatStudioSelectionToolbar';
import { NotebookChatSelectionPopover } from './NotebookChatSelectionPopover';
import { ChatInput } from './ChatInput';
import { ChatListSidebar } from './ChatListSidebar';
import { MessageCircle, RefreshCw, WifiOff, AlertTriangle, Menu, X } from 'lucide-react';
import { useApi } from '@/hooks/useApi';
import { useSourceContext } from '@/contexts/SourceContext';
import { useChatContext } from '@/contexts/ChatContext';
import { useUserContext } from '@/contexts/UserContext';
import { handleApiError, getUserFriendlyMessage } from '@/lib/error-handler';
import { DEFAULT_NCERT_SUBJECTS_BY_CLASS } from '@/config/ncertSubjectsByClass';
import type { NcertTutorChapterOption } from '@/lib/api-client';
import { useSources } from '@/hooks/useSources';
import { useNotebookScopeId } from '@/contexts/NotebookContext';
import { ChatMessagesSkeleton } from '@/components/skeleton';
import { useValidSelectedSourceIds } from '@/hooks/useValidSelectedSourceIds';
import { useStudioChatBridgeSafe } from '@/contexts/StudioChatBridgeContext';
import { TutorNotebookHeader } from './TutorNotebookHeader';
import { formatTutorScopeChip, type TutorScopeSettings } from '@/lib/tutor-ncert-source';

/** Shown after upload when ingestion completes; triggers same map-reduce path as summary intent. */
const POST_UPLOAD_SUMMARY_PROMPT =
  'Summarize the entire document I just added.';

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
  isSummary?: boolean;
  citations?: Citation[];
  messageId?: string;
  question?: string; // The question that was asked (for assistant messages)
  followUps?: string[];
}

type ChatInterfaceMode = 'dashboard' | 'tutor';

type HandleSendOptions = {
  /** Same pipeline as explicit whole-document summary; requires exactly one source. */
  forceWholeFileMapReduce?: boolean;
  /** Start a fresh chat (e.g. post-upload auto-summary). */
  forceNewChat?: boolean;
  newChatTitle?: string;
  /** When set, overrides dashboard NCERT checkbox for this request only. */
  includeNcertGlobalOverride?: boolean;
  /**
   * Do not show or persist a user message; only the assistant reply appears (e.g. post-upload auto-summary).
   * The `message` string is still sent to the API for routing.
   */
  omitUserFacingPrompt?: boolean;
};

interface TutorNcertScope extends TutorScopeSettings {}

interface ChatInterfaceProps {
  mode?: ChatInterfaceMode;
  appearance?: 'dashboard' | 'notebook';
  defaultNcertScope?: TutorNcertScope | null;
  tutorSuggestions?: { label: string; prompt: string }[];
  tutorBootstrapReady?: boolean;
  tutorBootstrapping?: boolean;
  tutorOverviewChatId?: string;
}

export function ChatInterface({
  mode = 'dashboard',
  appearance = 'dashboard',
  defaultNcertScope = null,
  tutorSuggestions,
  tutorBootstrapReady = true,
  tutorBootstrapping = false,
  tutorOverviewChatId,
}: ChatInterfaceProps) {
  const isTutorMode = mode === 'tutor';
  const isNotebookAppearance = appearance === 'notebook';
  const isLockedNotebookTutor = isTutorMode && isNotebookAppearance && defaultNcertScope != null;
  const lockedNcertScope = useMemo(() => {
    if (!defaultNcertScope) return null;
    const subject = String(defaultNcertScope.subject_slug ?? defaultNcertScope.subject_key ?? '')
      .trim()
      .toLowerCase()
      .replace(/\s+/g, '_');
    const chapterName = String(
      defaultNcertScope.filter_chapter_name ??
        defaultNcertScope.chapter_name ??
        defaultNcertScope.chapter_title ??
        '',
    )
      .trim()
      .toLowerCase();
    const conceptRaw = defaultNcertScope.concept;
    const concept =
      conceptRaw && String(conceptRaw).trim() && String(conceptRaw).trim().toLowerCase() !== 'all'
        ? String(conceptRaw).trim()
        : '';
    return {
      class_num: defaultNcertScope.class_num,
      subject,
      chapter_no: defaultNcertScope.chapter_no,
      chapter_name: chapterName || undefined,
      concept,
    };
  }, [defaultNcertScope]);
  const scopeChipLabel = defaultNcertScope ? formatTutorScopeChip(defaultNcertScope) : '';
  const [messages, setMessages] = useState<Message[]>([]);
  const { currentChatId, setCurrentChat, setCurrentChatId } = useChatContext();
  const [isLoading, setIsLoading] = useState(false);
  const [turnCount, setTurnCount] = useState(0);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [isOnline, setIsOnline] = useState(true);
  const [isLoadingChat, setIsLoadingChat] = useState(false);
  const [currentResponse, setCurrentResponse] = useState('');
  const [currentCitations, setCurrentCitations] = useState<Citation[]>([]);
  const [currentQuestion, setCurrentQuestion] = useState<string>('');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sidebarRefreshTrigger, setSidebarRefreshTrigger] = useState(0);
  /** Shown instead of "Thinking" while map-reduce runs after upload (omitUserFacingPrompt). */
  const [isAutoSummaryStreamLoading, setIsAutoSummaryStreamLoading] = useState(false);
  const [followUpsLoadingForId, setFollowUpsLoadingForId] = useState<string | null>(null);
  /** Exploratory notebooks: selected uploads are the default source of truth (NotebookLM parity). */
  const [includeNcertGlobal, setIncludeNcertGlobal] = useState(false);
  /** Optional Pinecone metadata filter (Class 12 only); null = all classes */
  const [ncertFilterClass, setNcertFilterClass] = useState<number | null>(null);
  /** Optional subject slug filter, e.g. science */
  const [ncertFilterSubject, setNcertFilterSubject] = useState('');
  const [ncertFilterChapterKey, setNcertFilterChapterKey] = useState('');
  const [ncertFilterConcept, setNcertFilterConcept] = useState('');
  const [scopeApplied, setScopeApplied] = useState(false);
  const [ncertSubjectsByClass, setNcertSubjectsByClass] = useState<Record<string, string[]>>(
    DEFAULT_NCERT_SUBJECTS_BY_CLASS
  );
  const [ncertChapterOptions, setNcertChapterOptions] = useState<NcertTutorChapterOption[]>([]);
  const subjectMap = isTutorMode ? ncertSubjectsByClass : DEFAULT_NCERT_SUBJECTS_BY_CLASS;
  const ncertSubjectOptions = (() => {
    if (ncertFilterClass != null) {
      return subjectMap[String(ncertFilterClass)] || [];
    }
    return Array.from(new Set(Object.values(subjectMap).flat())).sort();
  })();

  const formatNcertSubjectLabel = (subject: string) =>
    subject
      .split('_')
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ');

  const buildChapterOptionKey = (chapter: NcertTutorChapterOption) =>
    `${chapter.chapter_no ?? ''}::${(chapter.chapter_name || '').trim().toLowerCase()}::${(chapter.title || '')
      .trim()
      .toLowerCase()}`;

  const formatChapterLabel = (chapter: NcertTutorChapterOption) => {
    const parts: string[] = [];
    if (chapter.chapter_no != null) {
      parts.push(`Ch. ${chapter.chapter_no}`);
    }
    if (chapter.chapter_name) {
      parts.push(chapter.chapter_name);
    } else if (chapter.title) {
      parts.push(chapter.title);
    }
    return parts.join(' - ') || 'Untitled chapter';
  };

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatMessagesScrollRef = useRef<HTMLDivElement>(null);
  const studioChatBridge = useStudioChatBridgeSafe();
  const lastUserMessageRef = useRef<string>('');
  /** Retry after error for streams that did not show a user prompt (auto-upload summary). */
  const lastHiddenStreamRetryRef = useRef<{
    message: string;
    sourceIds: string[];
    retryOptions: Omit<HandleSendOptions, 'forceNewChat' | 'newChatTitle'>;
  } | null>(null); 
  const responseAccumulatorRef = useRef<string>(''); 
  const citationsAccumulatorRef = useRef<Citation[]>([]); 
  const hasFetchedRecentRef = useRef(false);
  const uploadAutoSummaryRunRef = useRef<string | null>(null);
  const latestAssistantIdRef = useRef<string | null>(null);

  const { apiClient } = useApi();
  const { loading: userContextLoading } = useUserContext();
  const notebookId = useNotebookScopeId();
  const { data: sourcesList = [] } = useSources(notebookId);
  const {
    setSelectedSources,
    pendingUploadSummarySourceId,
    clearPendingUploadAutoSummary,
    postUploadAutoSummaryScheduledRef,
  } = useSourceContext();
  const { validSelectedIds: selectedSourceIds, validSelectedCount: selectedSourceCount } =
    useValidSelectedSourceIds();
  const normalizedTutorSubject = ncertFilterSubject.trim().toLowerCase().replace(/\s+/g, '_');
  const selectedTutorChapter =
    ncertChapterOptions.find((chapter) => buildChapterOptionKey(chapter) === ncertFilterChapterKey) || null;
  const effectiveIncludeNcertGlobal = isTutorMode ? true : includeNcertGlobal;
  const requiresSelectedSource = !isTutorMode;
  const chatBusy = isLoading || isStreaming || isLoadingChat || !isOnline;
  const needsSourceToSend = requiresSelectedSource && selectedSourceCount === 0;
  const chatDisabled = isNotebookAppearance
    ? chatBusy
    : chatBusy || needsSourceToSend;
  const sendDisabled = chatBusy || needsSourceToSend;
  const chatDisabledReason = !isOnline
    ? 'Reconnect to the internet to continue chatting.'
    : needsSourceToSend
      ? isNotebookAppearance
        ? 'Select at least one source to send a message.'
        : 'Select at least one source to enable dashboard chat.'
      : null;
  const chatHelperText = isLockedNotebookTutor
    ? `Searching ${scopeChipLabel || 'this NCERT chapter'}`
    : isTutorMode
      ? 'Tutor Mode searches the NCERT global library only'
      : `${selectedSourceCount} source${selectedSourceCount === 1 ? '' : 's'} selected`;
  const emptyStateMessage = isLockedNotebookTutor
    ? `Ask anything about ${scopeChipLabel || 'this chapter'}. Answers are grounded in your NCERT scope.`
    : isTutorMode
      ? 'Ask anything from the NCERT library. Narrow the scope with class, subject, or chapter filters if needed.'
      : selectedSourceCount === 0
        ? 'Select at least one notebook source to enable dashboard chat. For NCERT-only questions, open Tutor Mode.'
        : 'Ask questions about your selected sources. Optionally enable NCERT Global Library to supplement answers.';

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

  // Task C.c: Load previous chats on page load — guarded against Strict Mode double-fire AND against UserContext not being ready
  useEffect(() => {
    if (hasFetchedRecentRef.current || userContextLoading) return;
    if (isLockedNotebookTutor && !tutorBootstrapReady) return;
    if (postUploadAutoSummaryScheduledRef.current) {
      hasFetchedRecentRef.current = true;
      return;
    }
    hasFetchedRecentRef.current = true;
    loadRecentChat();
  }, [userContextLoading, postUploadAutoSummaryScheduledRef, isLockedNotebookTutor, tutorBootstrapReady]);

  useEffect(() => {
    if (!isLockedNotebookTutor || !tutorSuggestions?.length) return;
    setMessages((prev) => {
      const hasUser = prev.some((m) => m.role === 'user');
      if (hasUser) return prev;
      for (let i = prev.length - 1; i >= 0; i -= 1) {
        if (prev[i].role !== 'assistant' || prev[i].followUps?.length) {
          continue;
        }
        const prompts = tutorSuggestions
          .map((item) => item.prompt)
          .filter((prompt) => Boolean(prompt?.trim()))
          .slice(0, 4);
        if (prompts.length === 0) return prev;
        const hydrated = [...prev];
        hydrated[i] = { ...hydrated[i], followUps: prompts };
        latestAssistantIdRef.current = hydrated[i].id;
        return hydrated;
      }
      return prev;
    });
  }, [isLockedNotebookTutor, tutorSuggestions]);

  useEffect(() => {
    if (!isLockedNotebookTutor) return;

    const onBootstrapComplete = (event: Event) => {
      const detail = (event as CustomEvent<{ chat_id?: string | null }>).detail;
      const chatId = detail?.chat_id || tutorOverviewChatId;
      if (chatId) {
        void loadChat(chatId);
      } else {
        hasFetchedRecentRef.current = false;
        void loadRecentChat();
      }
      setSidebarRefreshTrigger((prev) => prev + 1);
    };

    window.addEventListener('tutorBootstrapComplete', onBootstrapComplete);
    return () => window.removeEventListener('tutorBootstrapComplete', onBootstrapComplete);
  }, [isLockedNotebookTutor, tutorOverviewChatId]);

  useEffect(() => {
    if (isTutorMode) {
      setIncludeNcertGlobal(true);
    }
  }, [isTutorMode]);

  useEffect(() => {
    if (!defaultNcertScope || scopeApplied) return;
    const classNum = defaultNcertScope.class_num;
    const subjectSlug = defaultNcertScope.subject_slug || defaultNcertScope.subject_key;
    const chapterNo = defaultNcertScope.chapter_no;
    const chapterName = defaultNcertScope.chapter_name;
    const concept = defaultNcertScope.concept;

    if (classNum != null) setNcertFilterClass(classNum);
    if (subjectSlug) setNcertFilterSubject(String(subjectSlug));
    if (chapterNo != null && chapterName) {
      setNcertFilterChapterKey(`${chapterNo}::${chapterName.trim().toLowerCase()}::`);
    }
    if (concept) setNcertFilterConcept(String(concept));
    setScopeApplied(true);
  }, [defaultNcertScope, scopeApplied]);

  useEffect(() => {
    if (!isTutorMode || userContextLoading || isLockedNotebookTutor) {
      return;
    }

    let cancelled = false;
    const loadTutorFilters = async () => {
      try {
        const data = await apiClient.getNcertTutorFilters({
          class_num: ncertFilterClass ?? undefined,
          subject: normalizedTutorSubject || undefined,
        });
        if (cancelled || !data) {
          return;
        }

        if (data.subjects_by_class && Object.keys(data.subjects_by_class).length > 0) {
          setNcertSubjectsByClass(data.subjects_by_class);
        }
        setNcertChapterOptions(Array.isArray(data.chapters) ? data.chapters : []);
      } catch (error) {
        if (!cancelled) {
          setNcertChapterOptions([]);
        }
      }
    };

    void loadTutorFilters();
    return () => {
      cancelled = true;
    };
  }, [apiClient, isTutorMode, ncertFilterClass, normalizedTutorSubject, userContextLoading]);

  useEffect(() => {
    if (!selectedTutorChapter && ncertFilterChapterKey) {
      setNcertFilterChapterKey('');
    }
  }, [ncertFilterChapterKey, selectedTutorChapter]);

  // Scroll to bottom when messages or current streaming response changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentResponse, isLoading]);

  // Track completed user/assistant turn pairs for summarize option
  useEffect(() => {
    const nonSummaryMessages = messages.filter((m) => !m.isSummary);
    const userCount = nonSummaryMessages.filter((m) => m.role === 'user').length;
    const assistantCount = nonSummaryMessages.filter((m) => m.role === 'assistant').length;
    const pairs = Math.min(userCount, assistantCount);
    setTurnCount(pairs);
  }, [messages]);

  // Task C.c: Load the most recent chat on mount (retry: cold API/DB can exceed a single short window)
  const loadRecentChat = async () => {
    if (postUploadAutoSummaryScheduledRef.current) {
      setIsLoadingChat(false);
      return;
    }
    const maxAttempts = 3;
    try {
      setIsLoadingChat(true);
      let lastError: unknown;
      for (let attempt = 0; attempt < maxAttempts; attempt++) {
        try {
          if (attempt > 0) {
            await new Promise((r) => setTimeout(r, 600 * attempt));
          }
          if (tutorOverviewChatId) {
            await loadChat(tutorOverviewChatId);
            return;
          }
          const chatList = await apiClient.listChats(1, 0, notebookId);
          if (chatList.chats && chatList.chats.length > 0) {
            await loadChat(chatList.chats[0].id);
          }
          return;
        } catch (e) {
          lastError = e;
          if (attempt === maxAttempts - 1) {
            console.warn('Failed to load recent chat after retries:', lastError);
            // Do not set streamError — avoids a false "offline" banner when the server is slow or warming up.
          }
        }
      }
    } finally {
      setIsLoadingChat(false);
    }
  };

  const attachFollowUpsToAssistant = useCallback((targetId: string, followUps: string[]) => {
    if (followUps.length === 0) {
      setFollowUpsLoadingForId(null);
      return;
    }
    setFollowUpsLoadingForId(null);
    setMessages((prev) => {
      let matched = false;
      let matchedId: string | null = null;
      const updated = prev.map((msg) => {
        if (msg.id === targetId || msg.messageId === targetId) {
          matched = true;
          matchedId = msg.id;
          return { ...msg, followUps };
        }
        return msg;
      });
      if (!matched) {
        for (let i = updated.length - 1; i >= 0; i -= 1) {
          if (updated[i].role === 'assistant') {
            updated[i] = { ...updated[i], followUps };
            latestAssistantIdRef.current = updated[i].id;
            return updated;
          }
        }
        return updated;
      }
      if (matchedId) {
        latestAssistantIdRef.current = matchedId;
      }
      return updated;
    });
  }, []);

  const fetchTutorFollowUpsForMessage = useCallback(
    async ({
      assistantId,
      userMessage,
      assistantText,
    }: {
      assistantId: string;
      userMessage: string;
      assistantText: string;
    }) => {
      if (!isLockedNotebookTutor || !notebookId) return;
      setFollowUpsLoadingForId(assistantId);
      latestAssistantIdRef.current = assistantId;
      try {
        const result = await apiClient.getTutorFollowUps({
          notebook_id: notebookId,
          user_message: userMessage,
          assistant_message: assistantText,
        });
        const followUps = result.follow_ups?.filter(Boolean).slice(0, 3) ?? [];
        attachFollowUpsToAssistant(assistantId, followUps);
      } catch (error) {
        console.warn('Failed to load tutor follow-ups:', error);
        setFollowUpsLoadingForId(null);
      }
    },
    [apiClient, attachFollowUpsToAssistant, isLockedNotebookTutor, notebookId],
  );

  const hydrateOverviewFollowUps = useCallback(
    (formattedMessages: Message[]): Message[] => {
      if (!isLockedNotebookTutor || !tutorSuggestions?.length) {
        return formattedMessages;
      }
      const hasUser = formattedMessages.some((m) => m.role === 'user');
      if (hasUser) {
        return formattedMessages;
      }
      const prompts = tutorSuggestions
        .map((item) => item.prompt)
        .filter((prompt) => Boolean(prompt?.trim()))
        .slice(0, 4);
      if (prompts.length === 0) {
        return formattedMessages;
      }
      for (let i = formattedMessages.length - 1; i >= 0; i -= 1) {
        if (formattedMessages[i].role === 'assistant') {
          const hydrated = [...formattedMessages];
          hydrated[i] = { ...hydrated[i], followUps: prompts };
          latestAssistantIdRef.current = hydrated[i].id;
          return hydrated;
        }
      }
      return formattedMessages;
    },
    [isLockedNotebookTutor, tutorSuggestions],
  );

  const maybeFetchFollowUpsForLoadedChat = useCallback(
    (formattedMessages: Message[]) => {
      if (!isLockedNotebookTutor || !notebookId) return;
      const hasUser = formattedMessages.some((m) => m.role === 'user');
      if (!hasUser) return;

      let lastAssistantIdx = -1;
      let lastUserMessage = '';
      for (let i = formattedMessages.length - 1; i >= 0; i -= 1) {
        if (lastAssistantIdx === -1 && formattedMessages[i].role === 'assistant') {
          lastAssistantIdx = i;
        }
        if (formattedMessages[i].role === 'user') {
          lastUserMessage = formattedMessages[i].content?.trim() || '';
          break;
        }
      }
      if (lastAssistantIdx === -1) return;

      const assistant = formattedMessages[lastAssistantIdx];
      if (assistant.followUps?.length) {
        latestAssistantIdRef.current = assistant.id;
        return;
      }

      void fetchTutorFollowUpsForMessage({
        assistantId: assistant.id,
        userMessage: lastUserMessage,
        assistantText: displayAssistantText(assistant.content),
      });
    },
    [fetchTutorFollowUpsForMessage, isLockedNotebookTutor, notebookId],
  );

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
        setCurrentChat(chat);
        if (chat.messages && Array.isArray(chat.messages) && chat.messages.length > 0) {
          const formattedMessages: Message[] = chat.messages.map((msg: any) => {
            // Detect summary messages by checking if content starts with "Summary of this chat so far:"
            const isSummary = msg.content && msg.content.startsWith('Summary of this chat so far:');
            return {
              id: msg.id,
              role: msg.role as 'user' | 'assistant',
              content: msg.content,
              citations: msg.citations || [],
              messageId: msg.id,
              timestamp: new Date(msg.created_at).toLocaleTimeString(),
              isSummary: isSummary,
            };
          });
          const hydrated = hydrateOverviewFollowUps(formattedMessages);
          setMessages(hydrated);
          maybeFetchFollowUpsForLoadedChat(hydrated);
        } else {
          setMessages([]);
          latestAssistantIdRef.current = null;
        }
        setStreamError(null); // Clear error on success
      } else {
        setStreamError('Chat not found.');
        setCurrentChat(null);
        setMessages([]);
      }
    } catch (error: any) {
      console.error('Failed to load chat:', error);
      // Use standardized error handling
      const apiError = error.apiError || handleApiError(error);
      const errorMessage = getUserFriendlyMessage(apiError);
      
      setStreamError(errorMessage);
      setCurrentChat(null);
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
      const newChat = await apiClient.createChat(undefined, notebookId);
      setCurrentChat(newChat);
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
    setCurrentChat(null);
    setMessages([]);
    setStreamError(null);
  };

  const persistMessageWithRetry = async (
    chatId: string,
    role: 'user' | 'assistant',
    content: string,
    citations: any[],
    retries: number = 3
  ) => {
    let lastError: any = null;
    for (let attempt = 0; attempt < retries; attempt++) {
      try {
        return await apiClient.addMessageToChat(chatId, role, content, citations);
      } catch (error: any) {
        lastError = error;
        if (attempt < retries - 1) {
          await new Promise((r) => setTimeout(r, 500 * (attempt + 1)));
        }
      }
    }
    throw lastError;
  };

  const handleSend = async (
    message: string,
    activeSourceIds?: string[],
    options?: HandleSendOptions
  ) => {
    // Task A.e: Prevent sending if offline
    if (!navigator.onLine) {
      setStreamError("Network disconnected. Please check your internet connection.");
      return;
    }

    const sourceIds = isTutorMode ? [] : (activeSourceIds || selectedSourceIds);

    if (requiresSelectedSource && sourceIds.length === 0) {
      setStreamError('Select at least one source to enable dashboard chat.');
      return;
    }

    if (!message.trim()) return;
    if (isLoading && !(options?.forceNewChat && options?.forceWholeFileMapReduce)) return;

    const hideUserBubble = Boolean(options?.omitUserFacingPrompt);

    // Task A.f: Retry — visible sends use lastUserMessageRef; hidden-prompt streams use lastHiddenStreamRetryRef
    if (!hideUserBubble) {
      lastHiddenStreamRetryRef.current = null;
      lastUserMessageRef.current = message;
      setCurrentQuestion(message.trim());
    } else {
      lastUserMessageRef.current = '';
      setCurrentQuestion('');
      lastHiddenStreamRetryRef.current = {
        message,
        sourceIds: [...sourceIds],
        retryOptions: {
          forceWholeFileMapReduce: options?.forceWholeFileMapReduce,
          includeNcertGlobalOverride: options?.includeNcertGlobalOverride,
          omitUserFacingPrompt: true,
        },
      };
    }

    if (options?.forceNewChat) {
      resetStreamingState();
    }

    // Task C.b: Create chat if it doesn't exist (or always new chat for post-upload summary)
    let chatId: string | null = options?.forceNewChat ? null : currentChatId;
    if (!chatId) {
      try {
        setIsLoading(true);
        const newChat = await apiClient.createChat(options?.newChatTitle, notebookId);
        chatId = newChat.id;
        setCurrentChat(newChat);
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

    const persistChatId = chatId;
    if (!persistChatId) {
      setStreamError('Could not start a chat session. Please try again.');
      setIsLoading(false);
      return;
    }

    if (!hideUserBubble) {
      const userMessage: Message = {
        id: Date.now().toString(),
        role: 'user',
        content: message,
        timestamp: new Date().toLocaleTimeString(),
        question: message.trim(),
      };

      if (options?.forceNewChat) {
        setMessages([userMessage]);
      } else {
        setMessages((prev) => [...prev, userMessage]);
      }

      if (chatId) {
        try {
          const savedMessage = await apiClient.addMessageToChat(chatId, 'user', message, []);
          if (savedMessage && savedMessage.id) {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === userMessage.id
                  ? { ...msg, id: savedMessage.id, messageId: savedMessage.id }
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
    } else {
      if (options?.forceNewChat) {
        setMessages([]);
      }
      setTimeout(() => {
        setSidebarRefreshTrigger((prev) => prev + 1);
      }, 300);
    }
    // Reset all streaming state before sending
    resetStreamingState();
    setIsLoading(true);
    setStreamError(null);
    setIsAutoSummaryStreamLoading(hideUserBubble);

    try {
      const historySource =
        options?.forceNewChat || hideUserBubble ? [] : messages;
      const history = historySource.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const includeNcertThisRequest =
        options?.includeNcertGlobalOverride !== undefined
          ? options.includeNcertGlobalOverride
          : effectiveIncludeNcertGlobal;

      const scopedChapterNo = isLockedNotebookTutor
        ? lockedNcertScope?.chapter_no
        : defaultNcertScope?.chapter_no ?? selectedTutorChapter?.chapter_no ?? undefined;
      const scopedChapterName = isLockedNotebookTutor
        ? lockedNcertScope?.chapter_name
        : defaultNcertScope?.filter_chapter_name ??
          defaultNcertScope?.chapter_name ??
          selectedTutorChapter?.chapter_name ??
          undefined;
      const ncertClassOpt = isLockedNotebookTutor
        ? includeNcertThisRequest && lockedNcertScope?.class_num != null
          ? lockedNcertScope.class_num
          : undefined
        : includeNcertThisRequest && ncertFilterClass != null
          ? ncertFilterClass
          : undefined;
      const ncertSubjectOpt = isLockedNotebookTutor
        ? includeNcertThisRequest && lockedNcertScope?.subject
          ? lockedNcertScope.subject
          : undefined
        : includeNcertThisRequest && normalizedTutorSubject
          ? normalizedTutorSubject
          : undefined;
      const ncertChapterNoOpt =
        includeNcertThisRequest && scopedChapterNo != null ? scopedChapterNo : undefined;
      const ncertChapterNameOpt =
        includeNcertThisRequest && scopedChapterName ? scopedChapterName : undefined;
      const ncertConceptOpt = isLockedNotebookTutor
        ? includeNcertThisRequest && lockedNcertScope?.concept
          ? lockedNcertScope.concept
          : undefined
        : includeNcertThisRequest && ncertFilterConcept.trim()
          ? ncertFilterConcept.trim()
          : undefined;

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
            if (hideUserBubble) {
              lastHiddenStreamRetryRef.current = null;
            }
            const assistantMessage: Message = {
              id: (Date.now() + 1).toString(),
              role: 'assistant',
              content: finalResponseText, // Use final response (may be renumbered or original)
              citations: filteredCitations,
              timestamp: new Date().toLocaleTimeString(),
              question: currentQuestion,
            };
            latestAssistantIdRef.current = assistantMessage.id;
            setMessages((prev) => {
              const cleared = prev.map((msg) =>
                msg.role === 'assistant' ? { ...msg, followUps: undefined } : msg,
              );
              return [...cleared, assistantMessage];
            });

            if (isLockedNotebookTutor && notebookId) {
              void fetchTutorFollowUpsForMessage({
                assistantId: assistantMessage.id,
                userMessage: currentQuestion.trim(),
                assistantText: displayAssistantText(finalResponseText),
              });
            }

            // Clear streaming UI immediately so we don't show a duplicate temporary bubble
            // while persistence to DB is in progress.
            resetStreamingState();

            if (persistChatId) {
              void (async () => {
                try {
                  // Format citations for backend (ensure they have required fields)
                  const formattedCitations = filteredCitations.map((citation) => ({
                    source_id: citation.sourceId || citation.source_id || '',
                    chunk_id: citation.chunk_id || '',
                    text: citation.text || '',
                    page_number: citation.page_number || null,
                    score: citation.score || 0,
                  }));

                  const savedMessage = await persistMessageWithRetry(
                    persistChatId,
                    'assistant',
                    finalResponseText, // Use final response
                    formattedCitations,
                    3
                  );
                  if (savedMessage && savedMessage.id) {
                    const savedId = savedMessage.id;
                    if (latestAssistantIdRef.current === assistantMessage.id) {
                      latestAssistantIdRef.current = savedId;
                    }
                    setFollowUpsLoadingForId((loadingId) =>
                      loadingId === assistantMessage.id ? savedId : loadingId,
                    );
                    setMessages((prev) =>
                      prev.map((msg) =>
                        msg.id === assistantMessage.id || msg.messageId === assistantMessage.id
                          ? {
                              ...msg,
                              id: savedId,
                              messageId: savedId,
                            }
                          : msg,
                      ),
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
              })();
            } else {
              console.error('Cannot save assistant message: No chat ID');
            }
          } else {
            // Check if we have citations but no text - this might indicate a backend issue
            if (filteredCitations.length > 0) {
              setStreamError("Received citations but no text response. The model may have been blocked or encountered an error. Please try again.");
            } else {
              setStreamError("Received an empty response from the assistant. Please try again or rephrase your question.");
            }
          }
          
          // For non-text responses, still clear streaming state.
          if (!finalResponseText || !finalResponseText.trim()) {
            resetStreamingState();
          }
        },
        // onError - Task A.b: Handle streaming errors gracefully
        (error: string) => {
          console.error('Streaming error:', error);

          // Special handling for low-confidence fallback from backend
          const lowConfidencePrefix = 'LOW_CONFIDENCE:';
          if (error.startsWith(lowConfidencePrefix)) {
            const fallbackMessage = error.slice(lowConfidencePrefix.length).trim();
            setStreamError(fallbackMessage || 'Not enough reliable information found. Please rephrase or check the document.');
            setIsStreaming(false);
            // Do NOT persist the low-confidence answer; just clear streaming state
            resetStreamingState();
            return;
          }

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

            // Best-effort persistence of partial response so refresh/load does not lose it.
            if (persistChatId) {
              void (async () => {
                try {
                  const partialCitations = citationsAccumulatorRef.current.map((citation) => ({
                    source_id: citation.sourceId || citation.source_id || '',
                    chunk_id: citation.chunk_id || '',
                    text: citation.text || '',
                    page_number: citation.page_number || null,
                    score: citation.score || 0,
                  }));
                  const savedPartial = await persistMessageWithRetry(
                    persistChatId,
                    'assistant',
                    partialMessage.content,
                    partialCitations,
                    2
                  );
                  if (savedPartial && savedPartial.id) {
                    setMessages((prev) =>
                      prev.map((msg) =>
                        msg.id === partialMessage.id
                          ? { ...msg, id: savedPartial.id, messageId: savedPartial.id }
                          : msg
                      )
                    );
                  }
                } catch (_e) {
                  // Non-blocking: partial response is already visible in UI
                }
              })();
            }
          }
          
          // Always reset streaming state on error
          resetStreamingState();
        },
        includeNcertThisRequest,
        ncertClassOpt,
        ncertSubjectOpt,
        ncertChapterNoOpt,
        ncertChapterNameOpt,
        options?.forceWholeFileMapReduce === true,
        ncertConceptOpt,
        // onReplace — the primary answer was streamed live, but a retry / hallucination
        // guard fix / output formatting / moderation step changed the final text.
        // Reset the displayed text instead of appending to it.
        (text: string) => {
          responseAccumulatorRef.current = text;
          setCurrentResponse(text);
        }
      );
    } catch (error: any) {
      // Task A.b & A.e
      // Ensure we always set a string, not an Error object
      const errorMessage = error?.message || error?.apiError?.message || error?.toString() || 'Failed to connect to the chat service.';
      setStreamError(errorMessage);
      // Always reset streaming state on error
      resetStreamingState();
    } finally {
      // Safety net: streamChat can return without firing onDone (e.g. SSE ends without done event).
      setIsLoading(false);
      setIsStreaming(false);
      setIsAutoSummaryStreamLoading(false);
    }
  };

  const resetStreamingState = () => {
    setCurrentResponse('');
    setCurrentCitations([]);
    responseAccumulatorRef.current = '';
    citationsAccumulatorRef.current = [];
    setIsLoading(false);
    setIsStreaming(false);
    setIsAutoSummaryStreamLoading(false);
  };

  // After a source finishes indexing, open a new chat and run whole-file map-reduce once.
  useEffect(() => {
    if (isTutorMode || !pendingUploadSummarySourceId) return;

    const pid = pendingUploadSummarySourceId;
    const src = sourcesList.find((s) => s.id === pid);
    if (!src) return;

    if (src.status === 'error' || src.status === 'failed') {
      clearPendingUploadAutoSummary();
      uploadAutoSummaryRunRef.current = null;
      return;
    }

    const ready = src.status === 'indexed' || src.status === 'completed';
    if (!ready) return;

    if (uploadAutoSummaryRunRef.current === pid) return;
    uploadAutoSummaryRunRef.current = pid;

    const rawTitle = 'title' in src ? (src as { title?: string }).title : undefined;
    const fileName = 'file_name' in src ? (src as { file_name?: string }).file_name : undefined;
    const label = (rawTitle || fileName || '').trim();
    const newChatTitle = label ? `Summary: ${label.slice(0, 80)}` : undefined;

    void (async () => {
      try {
        setSelectedSources(new Set([pid]));
        await handleSend(POST_UPLOAD_SUMMARY_PROMPT, [pid], {
          forceNewChat: true,
          newChatTitle,
          forceWholeFileMapReduce: true,
          includeNcertGlobalOverride: false,
          omitUserFacingPrompt: true,
        });
        setSidebarRefreshTrigger((x) => x + 1);
      } catch (e) {
        console.error('[upload-auto-summary]', e);
      } finally {
        clearPendingUploadAutoSummary();
        uploadAutoSummaryRunRef.current = null;
      }
    })();
    // handleSend is intentionally omitted from deps to avoid re-firing on each render.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- one-shot when source becomes ready
  }, [
    isTutorMode,
    pendingUploadSummarySourceId,
    sourcesList,
    clearPendingUploadAutoSummary,
    setSelectedSources,
  ]);

  // Task A.f: Retry functionality
  const handleRetry = () => {
    const hidden = lastHiddenStreamRetryRef.current;
    if (hidden) {
      setStreamError(null);
      handleSend(hidden.message, hidden.sourceIds, {
        ...hidden.retryOptions,
        forceNewChat: false,
      });
      return;
    }
    if (lastUserMessageRef.current) {
      setStreamError(null);
      handleSend(lastUserMessageRef.current);
    }
  };

  // Summarize chat history to reduce token usage and keep brief context
  const handleSummarizeChat = async () => {
    if (!currentChatId) {
      setStreamError('No active chat to summarize.');
      return;
    }

    try {
      setIsLoading(true);
      setStreamError(null);
      const savedSummary = await apiClient.summarizeChat(currentChatId);

      const summaryMessage: Message = {
        id: savedSummary.id,
        role: 'assistant',
        content: savedSummary.content,
        citations: savedSummary.citations || [],
        timestamp: new Date(savedSummary.created_at).toLocaleTimeString(),
        isSummary: true,
        messageId: savedSummary.id,
      };

      // Append summary into the same thread (do not delete existing messages)
      setMessages((prev) => [...prev, summaryMessage]);
      setStreamError(null);
      resetStreamingState();
      
      // Refresh sidebar to show updated message count
      setSidebarRefreshTrigger((prev) => prev + 1);
    } catch (error: any) {
      console.error('Failed to summarize chat:', error);
      const apiError = error.apiError || handleApiError(error);
      const errorMessage = getUserFriendlyMessage(apiError);
      setStreamError(`Failed to summarize chat: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  };

  const hasUserMessageInChat = messages.some((m) => m.role === 'user');

  const latestAssistantMessageId = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i].role === 'assistant' && !messages[i].isSummary) {
        return messages[i].id;
      }
    }
    return null;
  }, [messages]);

  useEffect(() => {
    if (isTutorMode || !studioChatBridge) return;
    const transcript = messages
      .filter((m) => (m.content || '').trim())
      .map((m) => {
        const c =
          m.role === 'assistant'
            ? displayAssistantText(m.content)
            : m.content.trim();
        return `${m.role === 'user' ? 'User' : 'Assistant'}: ${c}`;
      })
      .join('\n\n');
    studioChatBridge.setChatTranscript(transcript);
  }, [messages, isTutorMode, studioChatBridge]);

  return (
    <div className={`flex h-full ${isNotebookAppearance ? 'notebook-chat-shell bg-white' : 'bg-surface'}`}>
      {/* Chat List Sidebar */}
      <div className={`${sidebarOpen ? (isNotebookAppearance ? 'w-52' : 'w-64') : 'w-0'} transition-all duration-300 overflow-hidden ${isNotebookAppearance ? 'border-r border-[var(--color-home-border)]' : 'border-r border-border-default'}`}>
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
      <div className="flex-1 flex flex-col min-w-0 relative">
        {!isTutorMode && !isNotebookAppearance && (
          <ChatStudioSelectionToolbar
            scrollContainerRef={chatMessagesScrollRef}
            enabled={Boolean(studioChatBridge)}
          />
        )}
        {isNotebookAppearance && (
          <NotebookChatSelectionPopover scrollContainerRef={chatMessagesScrollRef} />
        )}
        {/* Task A.e: Network status indicator */}
        {!isOnline && (
          <div className="bg-red-600 text-white text-xs py-1.5 px-4 flex items-center justify-center gap-2">
            <WifiOff className="w-3 h-3" />
            Offline Mode: Check your connection to continue chatting
          </div>
        )}

        <div className={`${isNotebookAppearance ? 'h-12 px-3 border-b border-[var(--color-home-border)]' : 'h-14 px-4 border-b border-border-default'} flex items-center`}>
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className={`p-1.5 rounded-lg transition-colors ${isNotebookAppearance ? 'hover:bg-[var(--color-brand-surface)] text-[var(--color-home-label)] hover:text-[var(--color-brand-text)]' : 'hover:bg-surface-hover text-text-secondary hover:text-text-primary'}`}
                title={sidebarOpen ? 'Hide sidebar' : 'Show sidebar'}
              >
                {sidebarOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
              </button>
              <div className="flex items-center gap-2 min-w-0">
                {!isNotebookAppearance && <MessageCircle className="w-5 h-5 text-text-secondary" />}
                {isLockedNotebookTutor && defaultNcertScope ? (
                  <TutorNotebookHeader scope={defaultNcertScope} />
                ) : (
                  <h1 className={`${isNotebookAppearance ? 'text-[15px] font-bold text-[var(--color-home-text)]' : 'text-lg font-medium text-text-primary'}`}>
                    {isTutorMode ? 'Tutor Mode' : isNotebookAppearance ? 'Exploratory' : 'Chat'}
                  </h1>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {/* Summarize Chat Button - shown after 5 completed question/answer turns */}
              {turnCount >= 5 && !isNotebookAppearance && (
                <button
                  onClick={handleSummarizeChat}
                  disabled={isLoading || isStreaming || isLoadingChat}
                  className="px-3 py-1.5 text-xs font-semibold bg-surface-subtle border border-border-default rounded-lg text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Summarize chat so far
                </button>
              )}
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
        </div>

      <div ref={chatMessagesScrollRef} className={`flex-1 overflow-y-auto ${isNotebookAppearance ? 'notebook-chat-scroll px-3 py-3' : 'px-4 py-4'}`}>
        {isLoadingChat || (isLockedNotebookTutor && tutorBootstrapping) ? (
          <ChatMessagesSkeleton />
        ) : messages.length === 0 && !currentChatId ? (
          <div className="flex flex-col items-center justify-center h-full p-8">
              <p className="text-text-secondary text-center mb-2">{emptyStateMessage}</p>
          </div>
        ) : (
          <div className={`${isNotebookAppearance ? 'max-w-none space-y-4' : 'max-w-3xl mx-auto space-y-6'}`}>
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                role={message.role}
                content={message.content}
                citations={message.citations}
                timestamp={message.timestamp}
                messageId={message.messageId || message.id}
                question={message.question}
                followUps={
                  isLockedNotebookTutor &&
                  message.role === 'assistant' &&
                  message.id === latestAssistantMessageId
                    ? message.followUps
                    : undefined
                }
                followUpsLoading={
                  isLockedNotebookTutor &&
                  message.role === 'assistant' &&
                  message.id === latestAssistantMessageId &&
                  followUpsLoadingForId === message.id
                }
                onFollowUpClick={
                  isLockedNotebookTutor && message.role === 'assistant'
                    ? (prompt) => void handleSend(prompt)
                    : undefined
                }
                appearance={appearance}
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
                    appearance={appearance}
                    showActions={false}
                  />
                ) : (
                  <div className="flex items-center gap-3 p-4 bg-surface-subtle rounded-2xl w-fit">
                    <div className="flex gap-1">
                      <div className="w-1.5 h-1.5 bg-text-tertiary rounded-full animate-bounce [animation-delay:-0.3s]" />
                      <div className="w-1.5 h-1.5 bg-text-tertiary rounded-full animate-bounce [animation-delay:-0.15s]" />
                      <div className="w-1.5 h-1.5 bg-text-tertiary rounded-full animate-bounce" />
                    </div>
                    <span
                      className={
                        isAutoSummaryStreamLoading
                          ? 'text-xs font-medium text-text-tertiary tracking-wide'
                          : 'text-xs font-medium text-text-tertiary uppercase tracking-wider'
                      }
                    >
                      {isAutoSummaryStreamLoading
                        ? 'Generating document summary…'
                        : 'Thinking'}
                    </span>
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

        <div className={`${isNotebookAppearance ? 'p-3 border-t border-[var(--color-home-border)] bg-white' : 'p-4 bg-surface border-t border-border-default'} space-y-3`}>
          <div className={`flex flex-col gap-2 ${isNotebookAppearance ? '' : 'max-w-3xl mx-auto'}`}>
            {!isLockedNotebookTutor && isTutorMode ? (
              <div className="rounded-2xl border border-border-default bg-surface-subtle px-4 py-3">
                <p className="text-sm font-medium text-text-primary">
                  Tutor Mode always uses the NCERT Global Library.
                </p>
                <p className="mt-1 text-xs text-text-secondary">
                  Narrow the search scope with class, subject, and chapter filters.
                </p>
              </div>
            ) : !isLockedNotebookTutor ? (
              <label className={`flex items-center gap-2 cursor-pointer select-none ${isNotebookAppearance ? 'text-[11px] text-[var(--color-home-text-muted)] px-1' : 'text-sm text-text-secondary'}`}>
                <input
                  type="checkbox"
                  checked={includeNcertGlobal}
                  onChange={(e) => setIncludeNcertGlobal(e.target.checked)}
                  className="rounded border-border-default"
                />
                <span>{isNotebookAppearance ? 'NCERT Global Library' : 'Use NCERT Global Library'}</span>
              </label>
            ) : null}
            {isTutorMode && !isLockedNotebookTutor && (
              <div className="flex flex-wrap items-center gap-3 text-sm">
                <label className="flex items-center gap-2 text-text-secondary">
                  <span className="whitespace-nowrap">Filter class</span>
                  <select
                    value={ncertFilterClass === null ? '' : String(ncertFilterClass)}
                    onChange={(e) => {
                      const v = e.target.value;
                      const nextClass = v === '' ? null : parseInt(v, 10);
                      setNcertFilterClass(nextClass);
                      const nextSubjectOptions = nextClass == null
                        ? Array.from(new Set(Object.values(subjectMap).flat()))
                        : (subjectMap[String(nextClass)] || []);
                      if (ncertFilterSubject && !nextSubjectOptions.includes(ncertFilterSubject)) {
                        setNcertFilterSubject('');
                      }
                      setNcertFilterChapterKey('');
                    }}
                    className="rounded-lg border border-border-default bg-background px-2 py-1 text-text-primary text-sm"
                  >
                    <option value="">All classes</option>
                    {[12].map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex items-center gap-2 text-text-secondary min-w-[200px] flex-1">
                  <span className="whitespace-nowrap">Subject</span>
                  <select
                    value={ncertFilterSubject}
                    onChange={(e) => {
                      setNcertFilterSubject(e.target.value);
                      setNcertFilterChapterKey('');
                    }}
                    className="flex-1 min-w-0 rounded-lg border border-border-default bg-background px-2 py-1 text-text-primary text-sm"
                  >
                    <option value="">All subjects</option>
                    {ncertSubjectOptions.map((subject) => (
                      <option key={subject} value={subject}>
                        {formatNcertSubjectLabel(subject)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex items-center gap-2 text-text-secondary min-w-[220px] flex-1">
                  <span className="whitespace-nowrap">Chapter</span>
                  <select
                    value={ncertFilterChapterKey}
                    onChange={(e) => setNcertFilterChapterKey(e.target.value)}
                    disabled={ncertChapterOptions.length === 0}
                    className="flex-1 min-w-0 rounded-lg border border-border-default bg-background px-2 py-1 text-text-primary text-sm"
                  >
                    <option value="">
                      {ncertChapterOptions.length === 0 ? 'Select class or subject first' : 'All chapters'}
                    </option>
                    {ncertChapterOptions.map((chapter) => {
                      const optionKey = buildChapterOptionKey(chapter);
                      return (
                        <option key={optionKey} value={optionKey}>
                          {formatChapterLabel(chapter)}
                        </option>
                      );
                    })}
                  </select>
                </label>
              </div>
            )}
          </div>
          <ChatInput
            onSend={handleSend}
            disabled={chatDisabled}
            sendDisabled={sendDisabled}
            disabledReason={chatDisabledReason}
            helperText={chatHelperText}
            activeSourceIds={isTutorMode ? [] : selectedSourceIds}
            showSuggestedPrompts={!isLockedNotebookTutor && !hasUserMessageInChat}
            tutorSuggestions={tutorSuggestions}
            appearance={appearance}
          />
        </div>
      </div>
    </div>
  );
}
