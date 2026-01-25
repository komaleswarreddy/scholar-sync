'use client';

import { createContext, useContext, useState, ReactNode, useEffect } from 'react';

interface SourceContextType {
  selectedSources: Set<string>;
  toggleSource: (sourceId: string) => void;
  removeSource: (sourceId: string) => void; // Added for Task D.d
  clearSelection: () => void;
  setSelectedSources: (sources: Set<string>) => void;
}

const SourceContext = createContext<SourceContextType | undefined>(undefined);

const LOCAL_STORAGE_KEY = 'selected_source_ids';

export function SourceProvider({ children }: { children: ReactNode }) {
  const [selectedSources, setSelectedSources] = useState<Set<string>>(new Set());
  const [isInitialized, setIsInitialized] = useState(false);

  // --- Task B: Persistence (Load from LocalStorage on mount) ---
  useEffect(() => {
    const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          setSelectedSources(new Set(parsed));
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
    setSelectedSources((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(sourceId)) {
        newSet.delete(sourceId);
      } else {
        newSet.add(sourceId);
      }
      return newSet;
    });
  };

  // --- Task D.d: Helper to remove selection if source is deleted ---
  const removeSource = (sourceId: string) => {
    setSelectedSources((prev) => {
      if (!prev.has(sourceId)) return prev;
      const newSet = new Set(prev);
      newSet.delete(sourceId);
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
