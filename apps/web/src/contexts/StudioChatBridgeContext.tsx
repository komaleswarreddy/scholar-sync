'use client';

import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';

export type StudioChatBridgeValue = {
  chatTranscript: string;
  setChatTranscript: (t: string) => void;
  hasChatContext: boolean;
};

const StudioChatBridgeContext = createContext<StudioChatBridgeValue | null>(null);

export function StudioChatBridgeProvider({ children }: { children: React.ReactNode }) {
  const [chatTranscript, setChatTranscriptState] = useState('');
  const setChatTranscript = useCallback((t: string) => {
    setChatTranscriptState((t || '').trim());
  }, []);
  const hasChatContext = useMemo(() => chatTranscript.trim().length > 0, [chatTranscript]);
  const value = useMemo(
    () => ({ chatTranscript, setChatTranscript, hasChatContext }),
    [chatTranscript, setChatTranscript, hasChatContext]
  );
  return (
    <StudioChatBridgeContext.Provider value={value}>{children}</StudioChatBridgeContext.Provider>
  );
}

export function useStudioChatBridge(): StudioChatBridgeValue {
  const ctx = useContext(StudioChatBridgeContext);
  if (!ctx) {
    throw new Error('useStudioChatBridge must be used within StudioChatBridgeProvider');
  }
  return ctx;
}

export function useStudioChatBridgeSafe(): StudioChatBridgeValue | null {
  return useContext(StudioChatBridgeContext);
}
