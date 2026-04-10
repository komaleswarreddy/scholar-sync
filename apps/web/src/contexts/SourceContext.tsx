'use client';

import {
  createContext,
  useContext,
  useState,
  ReactNode,
  useEffect,
  useRef,
  useCallback,
  type Dispatch,
  type MutableRefObject,
  type SetStateAction,
} from 'react';

interface SourceContextType {
  selectedSources: Set<string>;
  toggleSource: (sourceId: string) => void;
  removeSource: (sourceId: string) => void; // Added for Task D.d
  clearSelection: () => void;
  setSelectedSources: Dispatch<SetStateAction<Set<string>>>;
  /** Source id waiting for indexing, then dashboard runs auto map-reduce summary. */
  pendingUploadSummarySourceId: string | null;
  queueUploadAutoSummary: (sourceId: string) => void;
  clearPendingUploadAutoSummary: () => void;
  /** When true, skip loading the most recent chat on first paint (upload auto-summary pending). */
  postUploadAutoSummaryScheduledRef: MutableRefObject<boolean>;
}

const SourceContext = createContext<SourceContextType | undefined>(undefined);

const LOCAL_STORAGE_KEY = 'selected_source_ids';

export function SourceProvider({ children }: { children: ReactNode }) {
  const [selectedSources, setSelectedSources] = useState<Set<string>>(new Set());
  const [isInitialized, setIsInitialized] = useState(false);
  const [pendingUploadSummarySourceId, setPendingUploadSummarySourceId] = useState<string | null>(null);
  const postUploadAutoSummaryScheduledRef = useRef(false);

  const queueUploadAutoSummary = useCallback((sourceId: string) => {
    if (!sourceId) return;
    postUploadAutoSummaryScheduledRef.current = true;
    setPendingUploadSummarySourceId(sourceId);
  }, []);

  const clearPendingUploadAutoSummary = useCallback(() => {
    setPendingUploadSummarySourceId(null);
    postUploadAutoSummaryScheduledRef.current = false;
  }, []);

  // --- Task B: Persistence (Load from LocalStorage on mount) ---
  useEffect(() => {
    const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          const normalized = parsed
            .map((x) => String(x ?? '').trim())
            .filter((id) => id.length > 0);
          setSelectedSources(new Set(normalized));
        }
      } catch (e) {
        console.error("Failed to parse persisted selections:", e);
      }
    }
    setIsInitialized(true);
  }, []);

  // --- Task B: Persistence (Save to LocalStorage on change) ---
  useEffect(() => {
    if (isInitialized) {
      const arrayToSave = Array.from(selectedSources);
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(arrayToSave));
    }
  }, [selectedSources, isInitialized]);

  const toggleSource = (sourceId: string) => {
    const id = String(sourceId ?? '').trim();
    if (!id) return;
    setSelectedSources((prev) => {
      const newSet = new Set<string>();
      for (const x of prev) {
        newSet.add(String(x).trim());
      }
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  // --- Task D.d: Helper to remove selection if source is deleted ---
  const removeSource = (sourceId: string) => {
    const id = String(sourceId ?? '').trim();
    if (!id) return;
    setSelectedSources((prev) => {
      if (![...prev].some((x) => String(x).trim() === id)) return prev;
      const newSet = new Set<string>();
      for (const x of prev) {
        const k = String(x).trim();
        if (k && k !== id) newSet.add(k);
      }
      return newSet;
    });
  };

  const clearSelection = () => {
    setSelectedSources(new Set());
  };

  return (
    <SourceContext.Provider
      value={{
        selectedSources,
        toggleSource,
        removeSource,
        clearSelection,
        setSelectedSources,
        pendingUploadSummarySourceId,
        queueUploadAutoSummary,
        clearPendingUploadAutoSummary,
        postUploadAutoSummaryScheduledRef,
      }}
    >
      {children}
    </SourceContext.Provider>
  );
}

export function useSourceContext() {
  const context = useContext(SourceContext);
  if (!context) {
    throw new Error('useSourceContext must be used within SourceProvider');
  }
  return context;
}
